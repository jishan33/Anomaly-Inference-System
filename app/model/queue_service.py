
import json
import logging
import time
import uuid
from typing import TypedDict

from app.model.config import VIP_QUEUE, FREE_QUEUE
from app.model.metrics import QUEUE_INGRESS_TOTAL
from app.shared.redis import redis_circuit_breaker, redis_client

logger = logging.getLogger("queue_service")


class QueueJob(TypedDict):
    job_id: str
    transaction: dict
    created_at: float
    tier: str
    retry_count: int

def enqueue_job(redis_client, transaction: dict):
    job_id = str(uuid.uuid4())
    tier = transaction.get("tier")

    job = QueueJob(
        job_id = job_id,
        transaction= transaction,
        created_at= time.time(),
        tier= tier,
        retry_count= 0
    )
    queue_name = VIP_QUEUE if tier == "vip" else FREE_QUEUE
    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush(
                queue_name,
                json.dumps(job)
            ),
            operation_name=f"redis_enqueue_{tier}"
        )

        QUEUE_INGRESS_TOTAL.labels(tier).inc()
        return job_id

    except Exception as e:
        logger.error(f'redis unavailable during equeue {tier}: {e}')
        raise



def get_queue_depth(queue_name: str) -> int|None:
    try:
        queue_depth = redis_circuit_breaker.call(
            lambda: redis_client.llen(queue_name),
            operation_name=f"redis_llen {queue_name}"
        )
        return queue_depth
    except Exception as e:
        logger.error(f"redis is unavailable for llen operation: {e}")


