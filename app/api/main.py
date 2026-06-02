import logging
import random
import traceback
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware import Middleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

from app.api.anomaly_detect import anomaly_score, anomaly_volume_score, anomaly_customer_transaction_volume_score
from app.model.model import model_instance
from app.model.routes import router
from app.api.config import INSTANCE_ID, setup_logging
from app.shared.metrics import ANOMALY_COUNT, USER_RATE_LIMIT, REQUEST_COUNT
from app.api.request_logging_middleware import RequestLoggingMiddleware
from app.api.transaction_store import Transaction, append_to_redis, safe_get_customer_transaction_volume, \
    safe_get_volume, redis_circuit_breaker, generate_random_transaction
from app.api.validation import CustomerRequest
from app.shared.redis import get_redis_client

# Logging should be configured exactly once, at app startup!!!
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the model and share it via app.state    model_instance.load()
    yield {"model": model_instance}
    # Clean up on shutdown if needed

app = FastAPI(
    middleware=[Middleware(RequestLoggingMiddleware)],
    lifespan=lifespan
)

app.include_router(router)

# API
@app.post("/predict_amount")
def predict_amount(transaction: Transaction):
    score = anomaly_score(transaction)
    alert_flag = score > 0.7
    if alert_flag:
        ANOMALY_COUNT.labels(instance=INSTANCE_ID, type="amount").inc()
    return {
        "anomaly_score": score,
        "alert_flag": alert_flag
    }

@app.post("/ingest_and_detect_volume")
def predict_volume(transactions: List[Transaction], request: Request):
    request_id = getattr(request.state, "request_id", "unknown")
    append_to_redis(transactions, request_id)
    volume = safe_get_volume(request_id)

    logger.info(
            "ingest_batch",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "batch_size": len(transactions),
                    "volume_last_minute": volume
                }
            }
        )

    score = anomaly_volume_score(volume)
    alert_flag = score > 0.7
    if alert_flag:
        ANOMALY_COUNT.labels(instance=INSTANCE_ID, type="volume").inc()
    return {
        "volume_last_minute": volume,
        "anomaly_score": score,
        "alert_flag": alert_flag
    }

@app.post("/detect_customer_transaction_volume")
def predict_customer_transaction_volume(customer: CustomerRequest, request: Request ):
    request_id = getattr(request.state, "request_id", "unknown")
    customer_token = customer.customer_token
    volume = safe_get_customer_transaction_volume(customer_token, request_id)

    logger.info(
            "customer_check",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "customer": customer_token,
                    "volume_last_minute": volume
                }
            }
        )

    score = anomaly_customer_transaction_volume_score(volume)
    limited = score > 0.7
    if limited:
        USER_RATE_LIMIT.labels(instance= INSTANCE_ID).inc()
        logger.warning(
            "rate_limited",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "customer": customer_token,
                    "volume": volume
                }
            }
        )
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    return {
        "volume_last_minute": volume,
        "customer_token": customer_token,
        "anomaly_score": score,
    }

@app.get("/generate_transaction")
def generate_transaction():
    tx = generate_random_transaction()
    return tx

@app.get("/generate_transactions")
def generate_transactions():
    count = random.randint(1, 1000)

    transactions: List[Transaction] = [
        generate_random_transaction()
        for _ in range(count)
    ]
    return transactions


# Health
@app.get("/healthz")
def health():
    try:
        redis_client = get_redis_client()
        logger.info(f"REDIS_CLIENT: {redis_client}")
        redis_client.ping()
        return {"status": "okay", "instance": INSTANCE_ID}
    except Exception as e:
        logger.error(
            "redis_error",
            extra={
                "extra_data": {
                    "instance_id": INSTANCE_ID,
                    "error": str(e)
                }
            }
        )
        return {"status": "redis-unavailable", "instance": INSTANCE_ID}

@app.get("/live")
def live():
    return {
        "status": "alive",
        "instance": INSTANCE_ID
    }

@app.get("/ready")
def ready():
    return {
        "status": "ready",
        "instance": INSTANCE_ID
    }


# Debug
@app.get("/whoami")
def whoami():
    return {
        "instance": INSTANCE_ID
    }


@app.get("/debug/volume")
def debug_volume():
    # expose minimal info so we can observe per-instance store size
    return {
        "instance": INSTANCE_ID,
        "volume_last_minute": safe_get_volume()
    }

@app.get("/debug/circuit_breaker")
def debug_cb():
    return {
        "state": redis_circuit_breaker,
        "failure_count": redis_circuit_breaker.failure_count,
        "last_failure_time": str(redis_circuit_breaker.last_failure_time)
    }

# Metric
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.get("/test_metrics")
def test_metrics():
    REQUEST_COUNT.labels(
        instance=INSTANCE_ID,
        method="GET",
        endpoint="/test_metrics",
        status="200"
    ).inc()
    return {"ok": True}


# Exception Handler
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")

    logger.warning(
        "request_failed",
        extra={
            "extra_data": {
                "request_id": request_id,
                "path": request.url.path,
                "status_code": exc.status_code,
                "error_type": "HTTP_ERROR",
                "detail": exc.detail
            }
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "request_id": request_id
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")

    logger.error(
        "internal_error",
        extra={
            "extra_data": {
                "request_id": request_id,
                "path": request.url.path,
                "error_type": "INTERNAL_ERROR",
                "exception": str(exc),
                "trace": traceback.format_exc()
            }
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Something went wrong",
            "request_id": request_id
        }
    )