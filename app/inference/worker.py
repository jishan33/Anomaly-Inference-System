import json
import logging
import os
import time
import tritonclient.http as httpclient

from app.inference.batch import process_batch
from app.inference.config import FREE_QUEUE, VIP_QUEUE
from app.inference.scheduler import get_batch_scheduler
from app.shared.config import setup_logging
from prometheus_client import start_http_server

logger = logging.getLogger("worker")
logger.info("worker.py loaded")

WORKER_ROLE = os.getenv("WORKER_ROLE", "unknown")
TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "unknown")

def worker_loop():
    logger.info("Worker loop started...")

    while True:
        schedular =  get_batch_scheduler()

        vip_processed = False
        free_processed = False

        is_active_vip = WORKER_ROLE == "vip"
        is_active_shared = WORKER_ROLE == "shared"

        # ----------------------------------------------------------------------
        # VIP priority scheduling and only use active workers
        # ----------------------------------------------------------------------

        if is_active_vip:
            vip_processed = process_batch(VIP_QUEUE, "vip", schedular.vip_max_batch_size, schedular.vip_max_wait_time, WORKER_ROLE)
        elif is_active_shared:
            free_processed = process_batch(FREE_QUEUE, "free", schedular.free_max_batch_size, schedular.free_max_wait_time, WORKER_ROLE)


        # ---------------------------------------------------------------------
        # Idle detection
        # Dynamic Sleep: Only sleep if BOTH queues were completely empty.
        # ---------------------------------------------------------------------
        if not vip_processed and not free_processed:
            time.sleep(0.1)
#-----------------------------------------------------------------------------------------------
# python3 -m app.inference.worker
# Let's look at what Python does behind the scenes when you press enter:
# Locates the file: Python looks through your directories and finds app/inference/worker.py.
# Assigns the Crown: Because of that -m flag,
# Python treats this file as the absolute boss of the current execution.
# It sets:  __name__==__main__
#------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    setup_logging()
    start_http_server(9001)
    worker_loop()