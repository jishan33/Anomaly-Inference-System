import logging
import os
import time
from typing import NamedTuple
from prometheus_client import start_http_server

from app.api.temp_transaction_store import redis_client
from app.model.batch import process_batch
from app.shared.metrics import WORKER_ACTIVE_STATE, REDIS_OPERATION_FAILURES_TOTAL
from app.model.model import model_instance
from app.model.config import FREE_QUEUE, VIP_QUEUE
from app.model.queue_service import get_queue_depth
from app.model.scheduler import get_batch_scheduler
from app.shared.redis import redis_circuit_breaker

logger = logging.getLogger("worker")
logger.info("worker.py loaded")

WORKER_ROLE = os.getenv("WORKER_ROLE", "unknown")
WORKER_ID = os.getenv("WORKER_ID", "1")

start_http_server(9001)

model_instance.load()

class WorkerCounts(NamedTuple):
    vip: int
    shared: int

def get_active_workers()-> WorkerCounts|None:
    try:
        vip_raw, shared_raw = redis_circuit_breaker.call(
                lambda : redis_client.mget(
                "active_vip_workers",
                "active_shared_workers"
            ),
            operation_name="redis_mget"
        )
        return WorkerCounts(
            vip= int(vip_raw or 1),
            shared= int(shared_raw or 1)
        )
    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation="redis_mget").inc()
        logger.error(f"redis is unavailable for mget operation: {e}")




def worker_loop():
    logger.info("Worker loop started...")
    while True:
        schedular =  get_batch_scheduler()
        active_counts: WorkerCounts|None = get_active_workers()

        vip_depth: int|None = get_queue_depth(VIP_QUEUE)
        vip_processed = False
        free_processed = False

        if active_counts is not None:
            is_active_vip = (WORKER_ROLE == "vip" and int(WORKER_ID) <= active_counts.vip)
            is_active_shared = (WORKER_ROLE == "shared" and int(WORKER_ID) <= active_counts.shared)

            if is_active_vip or is_active_shared:
                 WORKER_ACTIVE_STATE.labels(
                     worker_role=WORKER_ROLE,
                     worker_id=WORKER_ID
                 ).set(1)
            else:
                WORKER_ACTIVE_STATE.labels(
                    worker_role=WORKER_ROLE,
                    worker_id=WORKER_ID
                ).set(0)
                time.sleep(1)
                continue

        # ----------------------------------------------------------------------
        # VIP priority scheduling and only use active workers
        # ----------------------------------------------------------------------

        if WORKER_ROLE == "vip":
            vip_processed = process_batch(VIP_QUEUE, "vip", schedular.vip_max_batch_size, schedular.vip_max_wait_time, WORKER_ROLE)
        elif WORKER_ROLE == "shared" and vip_depth is not None and vip_depth > 20:
            vip_processed = process_batch(VIP_QUEUE, "vip", schedular.free_max_batch_size, schedular.vip_max_wait_time, WORKER_ROLE)
        elif WORKER_ROLE == "shared":
            free_processed = process_batch(FREE_QUEUE, "free", schedular.free_max_batch_size, schedular.free_max_wait_time, WORKER_ROLE)


        # ---------------------------------------------------------------------
        # Idle detection
        # Dynamic Sleep: Only sleep if BOTH queues were completely empty.
        # ---------------------------------------------------------------------
        if not vip_processed and not free_processed:
            time.sleep(0.1)


if __name__ == "__main__":
    worker_loop()