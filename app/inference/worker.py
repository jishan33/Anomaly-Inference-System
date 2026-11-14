import asyncio
import logging
import os
import time

from app.inference.batch import process_batch
from app.inference.queue_config import Queue, Tier, QueueType
from app.inference.scheduler import get_batch_scheduler
from app.shared.config import setup_logging
from prometheus_client import start_http_server

logger = logging.getLogger("worker")
logger.info("worker.py loaded")

WORKER_ROLE = os.getenv("WORKER_ROLE", "unknown")
TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "unknown")

async def worker_loop():
    logger.info("Worker loop started...")

    while True:
        anomaly_predict_schedular = get_batch_scheduler(QueueType.ANOMALY_PREDICT)
        risk_summary_schedular = get_batch_scheduler(QueueType.RISK_SUMMARY)

        vip_anomaly_predict_processed = False
        free_anomaly_predict_processed = False
        vip_risk_summary_processed = False
        free_risk_summary_processed = False

        is_active_vip = WORKER_ROLE == "vip"
        is_active_shared = WORKER_ROLE == "shared"

        # ----------------------------------------------------------------------
        # VIP priority scheduling and only use active workers
        # ----------------------------------------------------------------------

        if is_active_vip:
            vip_anomaly_predict_processed = await process_batch(
                Queue.ANOMALY_PREDICT_VIP_QUEUE,
                Tier.VIP,
                anomaly_predict_schedular.vip_max_batch_size,
                anomaly_predict_schedular.vip_max_wait_time,
                WORKER_ROLE
            )
            vip_risk_summary_processed = await process_batch(
                Queue.RISK_SUMMARY_VIP_QUEUE,
                Tier.VIP,
                risk_summary_schedular.vip_max_batch_size,
                risk_summary_schedular.vip_max_wait_time,
                WORKER_ROLE
            )
        elif is_active_shared:
            free_anomaly_predict_processed = await process_batch(
                Queue.ANOMALY_PREDICT_FREE_QUEUE,
                Tier.FREE,
                anomaly_predict_schedular.free_max_batch_size,
                anomaly_predict_schedular.free_max_wait_time,
                WORKER_ROLE
            )

            free_risk_summary_processed = await process_batch(
                Queue.RISK_SUMMARY_FREE_QUEUE,
                Tier.FREE,
                risk_summary_schedular.free_max_batch_size,
                risk_summary_schedular.free_max_wait_time,
                WORKER_ROLE
            )


        # ---------------------------------------------------------------------
        # Idle detection
        # Dynamic Sleep: Only sleep if ALL queues were completely empty.
        # ---------------------------------------------------------------------
        if not vip_anomaly_predict_processed and not vip_risk_summary_processed and not free_anomaly_predict_processed and not free_risk_summary_processed:
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
    asyncio.run(worker_loop())