import logging
import random
import socket
import traceback
from typing import List
from fastapi import FastAPI
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware import Middleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest

from app.api.request_logging_middleware import RequestLoggingMiddleware
from app.api.transaction_store import Transaction, safe_get_volume, redis_circuit_breaker, generate_random_transaction
from app.inference.routes import router
from app.shared.redis import redis_client
from app.shared.config import setup_logging

# Logging should be configured exactly once, at app startup.
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    middleware=[Middleware(RequestLoggingMiddleware)],
)
HOSTNAME = socket.gethostname()
app.include_router(router)

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
        redis_client.ping()
        return {"status": "okay", "hostname": HOSTNAME}
    except Exception as e:
        logger.error(
            "redis_error",
            extra={
                "extra_data": {
                    "hostname": HOSTNAME,
                    "error": str(e)
                }
            }
        )
        return {"status": "redis-unavailable", "hostname": HOSTNAME}

@app.get("/livez")
def live():
    return {
        "status": "alive",
        "hostname": HOSTNAME
    }

@app.get("/readyz")
def ready():
    return {
        "status": "ready",
        "hostname": HOSTNAME
    }


# Debug
@app.get("/whoami")
def whoami():
    return {
        "hostname": HOSTNAME
    }


@app.get("/debug/volume")
def debug_volume():

    return {
        "hostname": HOSTNAME,
        "volume_last_minute": safe_get_volume()
    }

@app.get("/debug/circuit_breaker")
def debug_cb():
    return {
        "state": redis_circuit_breaker,
        "failure_count": redis_circuit_breaker.failure_count,
        "last_failure_time": str(redis_circuit_breaker.last_failure_time),
        "hostname": HOSTNAME
    }

# Metric
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")



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