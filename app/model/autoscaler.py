import logging
import time

from prometheus_client import start_http_server
from app.shared.redis import get_redis_client
from app.model.config import MIN_SHARED_WORKERS, MIN_VIP_WORKERS, SCALE_UP_QUEUE_DEPTH, MAX_SHARED_WORKERS, \
    MAX_VIP_WORKERS, SCALE_DOWN_QUEUE_DEPTH
from app.shared.metrics import SCALING_EVENTS_TOTAL, ACTIVE_SHARED_WORKERS, ACTIVE_VIP_WORKERS, \
    REDIS_OPERATION_FAILURES_TOTAL
from app.model.config import FREE_QUEUE, VIP_QUEUE
from app.model.queue_service import get_queue_depth
from app.shared.redis import redis_circuit_breaker

logger = logging.getLogger(__name__)

start_http_server(9005)

MIN_SCALE_INTERVAL_SECONDS = 30
POLL_INTERVAL_SECONDS = 5

redis_client = get_redis_client()

class Autoscaler:
    def __init__(self):
        self.active_shared_workers = MIN_SHARED_WORKERS
        self.active_vip_workers = MIN_VIP_WORKERS
        self.last_scale_time = time.time()
        self.set_workers_to_redis(worker_role="active_vip_workers")
        self.set_workers_to_redis(worker_role="active_shared_workers")

    def set_workers_to_redis(self, worker_role: str):
        try:
            if worker_role == "active_vip_workers":
                number_of_workers = self.active_vip_workers

            elif worker_role == "active_shared_workers":
                number_of_workers = self.active_shared_workers

            else:
                raise ValueError(f"Unknown worker role: {worker_role}")

            redis_circuit_breaker.call(
                lambda: redis_client.set(
                    worker_role,
                    number_of_workers,
                ),
                operation_name="redis_set",
            )

        except Exception as e:
            REDIS_OPERATION_FAILURES_TOTAL.labels(operation="redis_set").inc()
            logger.error(f"Redis is unavailable for set operation: {e}")

    def scale_shared_worker(self, target: int):
        target = max(MIN_SHARED_WORKERS, min(MAX_SHARED_WORKERS, target))

        if target != self.active_shared_workers:
            direction = ("up" if target > self.active_shared_workers else "down")

            SCALING_EVENTS_TOTAL.labels(tier="free", direction=direction).inc()

            self.active_shared_workers = target
            self.last_scale_time = time.time()
            self.set_workers_to_redis(worker_role="active_shared_workers")

            ACTIVE_SHARED_WORKERS.set(self.active_shared_workers)

            logger.info(f"[AUTOSCALER] "
                  f"shared workers -> "
                  f"{self.active_shared_workers}"
                  )

    def scale_vip_workers(self, target: int):
        target = max(MIN_VIP_WORKERS, min(MAX_VIP_WORKERS, target))

        if target != self.active_vip_workers:
            direction = (
                "up"
                if target > self.active_vip_workers
                else "down"
            )

            SCALING_EVENTS_TOTAL.labels(
                tier="vip",
                direction=direction
            ).inc()

            self.active_vip_workers = target
            self.last_scale_time = time.time()
            self.set_workers_to_redis(worker_role="active_vip_workers")

            ACTIVE_VIP_WORKERS.set(
                self.active_vip_workers
            )

            logger.info(
                f"[AUTOSCALER] "
                f"vip workers -> "
                f"{self.active_vip_workers}"
            )

    def autoscaler_loop(self):
        logger.info("[AUTOSCALER] loop running")
        while True:
            try:
                now = time.time()
                if now - self.last_scale_time < MIN_SCALE_INTERVAL_SECONDS:
                    continue

                free_depth: int|None = get_queue_depth(FREE_QUEUE)
                vip_depth: int|None = get_queue_depth(VIP_QUEUE)

                if free_depth is not None and vip_depth is not None:
                    # Free scaling logic
                    if free_depth > SCALE_UP_QUEUE_DEPTH and self.active_shared_workers < MAX_SHARED_WORKERS:
                        self.scale_shared_worker(self.active_shared_workers + 1)
                    elif free_depth < SCALE_DOWN_QUEUE_DEPTH and self.active_shared_workers > MIN_SHARED_WORKERS:
                        self.scale_shared_worker(self.active_shared_workers - 1)

                    # VIP scaling logic
                    if vip_depth > SCALE_UP_QUEUE_DEPTH and self.active_vip_workers < MAX_VIP_WORKERS:
                        self.scale_vip_workers(self.active_vip_workers + 1)
                    elif vip_depth < SCALE_DOWN_QUEUE_DEPTH and self.active_vip_workers > MIN_VIP_WORKERS:
                        self.scale_vip_workers(self.active_vip_workers - 1)

                else:
                    logger.error("[AUTOSCALER] Unable to fetch queue depths. Skipping scaling this cycle.")
            except Exception as e:
                logger.error(f"[AUTOSCALER] Unexpected error in loop: {e}")
            finally:
                time.sleep(POLL_INTERVAL_SECONDS)
