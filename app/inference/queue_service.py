
import json
import logging
import random
import time
import uuid
from typing import TypedDict
from pydantic import BaseModel

from app.api.transaction import Transaction
from app.inference.queue_config import Queue, RawJob, DEAD_LETTER_QUEUE, Tier, VIP_QUEUE_MAX_LOAD, \
    FREE_QUEUE_MAX_LOAD, QueueType
from app.shared.metrics import QUEUE_INGRESS_TOTAL, DEAD_LETTER_QUEUE_JOBS_TOTAL, DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL, \
    DLQ_PUSH_FAILURE_TOTAL, REDIS_OPERATION_FAILURES_TOTAL, LOAD_SHED_REQUESTS_TOTAL
from app.shared.redis import redis_circuit_breaker, redis_client

logger = logging.getLogger(__name__)

class QueueFullError(Exception):
    """Raised when a queue has reached its configured admission limit."""

class RedisUnavailableError(Exception):
    """Raised when Redis cannot be reached or a Redis operation fails."""

class QueueJob(BaseModel):
    job_id: str
    request: Transaction
    created_at: float
    tier: Tier
    queue_type: QueueType
    retry_count: int = 0

class DlqPayload(TypedDict):
    raw_job: RawJob
    reason: str
    failed_at: float

def get_queue_name(queue_type: QueueType, tier: Tier) -> Queue:
    _QUEUE_NAMES: dict[tuple[QueueType, Tier], Queue] = {
        (QueueType.ANOMALY_PREDICT, Tier.VIP): Queue.ANOMALY_PREDICT_VIP_QUEUE,
        (QueueType.ANOMALY_PREDICT, Tier.FREE): Queue.ANOMALY_PREDICT_FREE_QUEUE,
        (QueueType.RISK_SUMMARY, Tier.VIP): Queue.RISK_SUMMARY_VIP_QUEUE,
        (QueueType.RISK_SUMMARY, Tier.FREE): Queue.RISK_SUMMARY_FREE_QUEUE,
    }
    return _QUEUE_NAMES[(queue_type, tier)]

def _get_queue_limit(tier: Tier) -> int:
    if tier == Tier.VIP:
        return VIP_QUEUE_MAX_LOAD

    return FREE_QUEUE_MAX_LOAD

def get_queue_depth(queue_name: Queue) -> int|None:
    try:
        queue_depth: int = redis_circuit_breaker.call(
            lambda: redis_client.llen(queue_name),
            operation_name=f"redis_llen_{queue_name}"
        )
        return queue_depth

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_llen_{queue_name}").inc()
        logger.error("Redis unavailable for LLEN operation on %s: %s", queue_name, e)
        return None

def _verify_queue_availability(queue_name: Queue, tier: Tier):
    queue_depth = get_queue_depth(queue_name)
    if queue_depth is None:
        raise  RedisUnavailableError(
            f"Could not verify queue availability because Redis is unavailable. queue={queue_name}"
        )

    queue_limit = _get_queue_limit(tier)
    if queue_depth >= queue_limit:
        LOAD_SHED_REQUESTS_TOTAL.labels(tier=tier, reason=f"{queue_name}_depth_exceeded").inc()
        raise QueueFullError(f"{queue_name} max load reached. depth={queue_depth}, limit={queue_limit}")

def enqueue_job(queue_type: QueueType, request: Transaction) -> QueueJob:
    tier : Tier = random.choice((Tier.VIP, Tier.FREE))
    queue_name = get_queue_name(queue_type, tier)

    _verify_queue_availability(queue_name, tier)

    job = QueueJob(
        job_id = str(uuid.uuid4()),
        request= request,
        created_at= time.time(),
        tier= tier,
        queue_type= queue_type,
        retry_count= 0
    )

    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush(queue_name,job.model_dump_json()),
            operation_name="redis_enqueue"
        )

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_enqueue_{queue_name}").inc()
        logger.error(f'redis unavailable during enqueue {queue_name} job: {e}')
        raise RedisUnavailableError(
            f"Failed to enqueue {queue_name} job because Redis is unavailable."
        ) from e

    QUEUE_INGRESS_TOTAL.labels(queue_name).inc()

    return job

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
