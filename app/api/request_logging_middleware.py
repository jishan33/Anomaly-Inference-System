import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.config import INSTANCE_ID
from app.shared.metrics import REQUEST_COUNT, REQUEST_LATENCY, ERROR_COUNT

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        status_code = 500

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            ERROR_COUNT.labels(
                instance=INSTANCE_ID, type="http_error", status=str(status_code),
                endpoint=request.url.path).inc()
            # Let global handler deal with it
            raise e
        finally:
            process_time = time.time() - start_time
            REQUEST_COUNT.labels(
                instance=INSTANCE_ID,
                method=request.method,
                endpoint=request.url.path,
                status=str(status_code)
            ).inc()

            REQUEST_LATENCY.labels(
                instance=INSTANCE_ID,
                method=request.method,
                endpoint=request.url.path
            ).observe(process_time)

            if status_code >= 400:
                ERROR_COUNT.labels(
                instance=INSTANCE_ID,
                type="http_error",
                status=str(status_code),
                endpoint=request.url.path
            ).inc()

        # Log basic info
        logger.info(
            "request_completed",
            extra={
                "extra_data": {
                    "request_id": request_id,
                    "instance": INSTANCE_ID,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency": round(process_time, 4),
                }
            }
        )

        return response
