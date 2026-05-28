import logging
import random
import traceback
from datetime import timezone
from typing import List

from faker import Faker
from fastapi import FastAPI
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware import Middleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

from app.model.model import model_instance
from app.model.routes import router

from app.api.config import INSTANCE_ID, Config, setup_logging
from app.shared.metrics import ANOMALY_COUNT, USER_RATE_LIMIT, REQUEST_COUNT
from app.api.request_logging_middleware import RequestLoggingMiddleware
from app.api.temp_transaction_store import Transaction, append_to_redis, safe_get_customer_transaction_volume, safe_get_volume, \
    redis_client, redis_circuit_breaker
from app.api.validation import CustomerRequest

app = FastAPI(
    middleware=[Middleware(RequestLoggingMiddleware)],
)
setup_logging()

# Logging should be configured exactly once, at app startup!!!
logger = logging.getLogger(__name__)
config = Config()
app.include_router(router)

# Faker
fake = Faker()

def generate_random_transaction():
    random_date_obj = fake.date_time_between(start_date='-5m', end_date='now', tzinfo=timezone.utc)
    return Transaction(
        amount=fake.pyfloat(left_digits=6, right_digits=2, positive=True, min_value=0.01),
        created_at=random_date_obj.isoformat(),
        type=random.choice(["PAYMENT", "REFUND", "TRANSFER"]),
        customer_token=f"C_{fake.hexify(text='^^^^^^^^^^^^^^')}",
        transaction_token=f"TXN_{fake.uuid4()[:8].upper()}"
    )

# ------------------------
# Anomaly logic
# ------------------------
def anomaly_score(transaction: Transaction):
    amount = transaction.amount
    if config.NORMAL_MIN <= amount <= config.NORMAL_MAX:
        return 0.1

    if amount < config.NORMAL_MIN:
        deviation = config.NORMAL_MIN - amount
    else:
        deviation = amount - config.NORMAL_MAX

    score = min(1.0, deviation / config.NORMAL_MAX)
    return round(score, 2)


def anomaly_volume_score(volume: int):
    if config.NORMAL_VOLUME_MIN <= volume <= config.NORMAL_VOLUME_MAX:
        return 0.1
    if volume < config.NORMAL_VOLUME_MIN:
        deviation = config.NORMAL_VOLUME_MIN - volume
    else:
        deviation = volume - config.NORMAL_VOLUME_MAX

    score = min(1.0, deviation / config.NORMAL_VOLUME_MAX)
    return round(score, 2)


def anomaly_customer_transaction_volume_score(volume: int):
    if config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN <= volume <= config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX:
        return 0.1
    if volume < config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN:
        deviation = config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN - volume
    else:
        deviation = volume - config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX

    score = min(1.0, deviation / config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX)
    return round(score, 2)


# ------------------------
# API
# ------------------------
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


@app.get("/generate")
def generate():
    tx = generate_random_transaction()
    return tx


@app.get("/generate_batch")
def generate_batch():
    count = random.randint(1, 1000)

    transactions: List[Transaction] = [
        generate_random_transaction()
        for _ in range(count)
    ]
    return transactions


# debug endpoint
@app.get("/debug/volume")
def debug_volume1():
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


@app.get("/healthz")
def health():
    try:
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

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

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

@app.get("/test_metrics")
def test_metrics():
    REQUEST_COUNT.labels(
        instance=INSTANCE_ID,
        method="GET",
        endpoint="/test_metrics",
        status="200"
    ).inc()
    return {"ok": True}

@app.on_event("startup")
def load_model():
    model_instance.load()
