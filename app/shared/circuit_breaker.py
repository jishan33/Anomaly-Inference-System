import logging
import time

from app.api.config import INSTANCE_ID
from app.shared.metrics import CIRCUIT_BREAKER_STATE
from enum import Enum
from typing import Callable, TypeVar

logger = logging.getLogger("circuit_breaker")


T = TypeVar("T")

class CircuitBreakerError(Exception):
    pass

class CircuitBreakerOpenError(CircuitBreakerError):
    pass

class CircuitBreakerExecutionError(CircuitBreakerError):
    pass
# ------------------------
# CLOSED → normal
# OPEN → block calls
# HALF_OPEN → test recovery
#
# Circuit breaker prevents cascading failures by short-circuiting calls
# when a dependency is unhealthy, using CLOSED, OPEN, HALF-OPEN states.


# Core idea

# CLOSED:
#     allow requests
#     count failures
#
#     if too many failures → OPEN
#
# OPEN:
#     reject immediately
#
#     after timeout → HALF_OPEN
#
# HALF_OPEN:
#     allow 1 test request
#
#     if success → CLOSED
#     if failure → OPEN again
# ------------------------

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(
            self,
            failure_threshold=5,
            recovery_timeout=10
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # Wait some time before retrying

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED  # CLOSED | OPEN | HALF_OPEN

    def call(self, func: Callable[[], T], operation_name: str = "unknown", request_id: str = "unknown") -> T:
        """
        Wrap external calls (e.g. Redis)
        """
        # Step 1: Check if OPEN
        if self.state == CircuitBreakerState.OPEN:
            if self._can_attempt_recovery():
                self.state = CircuitBreakerState.HALF_OPEN
                CIRCUIT_BREAKER_STATE.labels(instance=INSTANCE_ID, operation=operation_name).set(2)
                logger.warning(
                    "circuit_half_open",
                    extra={"extra_data": {"operation": operation_name, "request_id": request_id}}
                )
            else:
                logger.warning(
                    "circuit_open_block",
                    extra={"extra_data": {"operation": operation_name, "request_id": request_id}}
                )
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        # Step 2: Try the function
        try:
            result = func()
            # Step 3: Success -> reset
            self._on_success(operation_name, request_id)
            return result

        except CircuitBreakerError:
             raise

        except Exception as e:
            # Step 4: Failure -> track
            self._on_failure(operation_name, e, request_id)
            raise CircuitBreakerExecutionError(
                f"Circuit breaker protected call failed: {operation_name}"
            ) from e

    # ------------------------
    # Internal helpers
    # ------------------------

    def _on_success(self, operation_name: str, request_id: str = "unknown"):
        CIRCUIT_BREAKER_STATE.labels(instance=INSTANCE_ID, operation=operation_name).set(0)
        if self.state in [CircuitBreakerState.HALF_OPEN, CircuitBreakerState.OPEN]:
            logger.info(
                "circuit_closed",
                extra={"extra_data": {"operation": operation_name, "request_id": request_id}}
            )
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED

    def _on_failure(self, operation_name: str, error: Exception, request_id: str = "unknown"):
        self.failure_count += 1
        self.last_failure_time = time.time()

        logger.error(
            "circuit_failure",
            extra={
                "extra_data": {
                    "operation": operation_name,
                    "request_id": request_id,
                    "failure_count": self.failure_count,
                    "error": str(error)
                }
            }
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            CIRCUIT_BREAKER_STATE.labels(instance=INSTANCE_ID, operation=operation_name).set(1)
            logger.error(
                "circuit_opened",
                extra={"extra_data": {"operation": operation_name, "request_id": request_id}}
            )

    def _can_attempt_recovery(self) -> bool:
        if self.last_failure_time is None:
            logger.error("circuit_invalid_state")
            return False

        return (time.time() - self.last_failure_time) >= self.recovery_timeout
