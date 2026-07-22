
import json
import logging
import time
import uuid
from typing import TypedDict, Any
from pydantic.v1 import BaseModel

from app.inference.config import VIP_QUEUE, FREE_QUEUE, RawJob, DEAD_LETTER_QUEUE, Tier
from app.shared.metrics import QUEUE_INGRESS_TOTAL, DEAD_LETTER_QUEUE_JOBS_TOTAL, DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL, \
    DLQ_PUSH_FAILURE_TOTAL, REDIS_OPERATION_FAILURES_TOTAL
from app.shared.redis import redis_circuit_breaker, redis_client

logger = logging.getLogger(__name__)

class QueueJob(BaseModel):
    job_id: str
    transaction: dict
    created_at: float
    tier: Tier
    retry_count: int

class DlqPayload(TypedDict):
    raw_job: RawJob
    reason: str
    failed_at: float

def enqueue_job(transaction: dict[str, Any]) -> QueueJob:
    job_id = str(uuid.uuid4())
    tier : Tier = transaction.get("tier", Tier.Free)

    job = QueueJob(
        job_id = job_id,
        transaction= transaction,
        created_at= time.time(),
        tier= tier,
        retry_count= 0
    )

    queue_name = VIP_QUEUE if tier == Tier.VIP else FREE_QUEUE
    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush(
                queue_name,
                job.json()
            ),
            operation_name=f"redis_enqueue_{tier}"
        )

        QUEUE_INGRESS_TOTAL.labels(tier).inc()
        return job

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_enqueue_{tier}").inc()
        logger.error(f'redis unavailable during enqueue {tier}: {e}')
        raise



def get_queue_depth(queue_name: str) -> int|None:
    try:
        queue_depth = redis_circuit_breaker.call(
            lambda: redis_client.llen(queue_name),
            operation_name=f"redis_llen_{queue_name}"
        )
        return queue_depth

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_llen_{queue_name}").inc()
        logger.error(f"redis is unavailable for llen operation: {e}")
        return None

def move_to_dlq(raw_job: RawJob, reason: str) -> bool:
    dlq_payload = DlqPayload(
        raw_job= raw_job.decode() if isinstance(raw_job, bytes) else raw_job,
        reason= reason,
        failed_at= time.time()
    )
    try:
        DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL.labels(reason=reason).inc()

        redis_circuit_breaker.call(
            lambda : redis_client.rpush(DEAD_LETTER_QUEUE, json.dumps(dlq_payload)),
            operation_name= "redis_dlq_push"
        )

        DEAD_LETTER_QUEUE_JOBS_TOTAL.labels(reason=reason).inc()
        logger.info(f"Moved job to DLQ. reason={reason}")
        return True
    except Exception as e:
        DLQ_PUSH_FAILURE_TOTAL.labels(reason=reason).inc()
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation="redis_dlq_push").inc()

        logger.error(
            f"CRITICAL: failed to move job to DLQ. "
            f"reason={reason}, error={e}, raw_job={raw_job}"
        )
        return False
