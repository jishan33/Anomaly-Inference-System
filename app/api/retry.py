import time
import random
import logging
from typing import Callable

from app.api.config import INSTANCE_ID
from app.shared.metrics import RETRY_COUNT

logger = logging.getLogger("retry")


def retry_with_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 0.05,  # 50ms
        max_delay: float = 1.0,
        exceptions=(Exception,),
        operation_name: str = "unknown"
):
    """
    Retry a function with exponential backoff + jitter.
    """

    for attempt in range(1, max_retries + 1):
        try:
            RETRY_COUNT.labels(instance=INSTANCE_ID, operation = operation_name).inc()
            return func()

        except exceptions as e:
            if attempt == max_retries:
                logger.error(
                    "retry_failed",
                    extra={
                        "extra_data": {
                            "operation": operation_name,
                            "attempt": attempt,
                            "error": str(e)
                        }
                    }
                )
                raise

            # exponential backoff with jitter
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter = random.uniform(0, delay / 2)
            sleep_time = delay + jitter

            logger.warning(
                "retry_attempt",
                extra={
                    "extra_data": {
                        "operation": operation_name,
                        "attempt": attempt,
                        "sleep_time": round(sleep_time, 4),
                        "error": str(e)
                    }
                }
            )

            time.sleep(sleep_time)
    return None
