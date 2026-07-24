
import json
import logging
import time
import uuid
from typing import TypedDict, Any
from pydantic.v1 import BaseModel

from app.inference.config import Queue, RawJob, DEAD_LETTER_QUEUE, Tier, VIP_QUEUE_MAX_LOAD, \
    FREE_QUEUE_MAX_LOAD
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
    transaction: dict
    created_at: float
    tier: Tier
    retry_count: int = 0

class DlqPayload(TypedDict):
    raw_job: RawJob
    reason: str
    failed_at: float

def _get_queue_name(tier: Tier) -> str:
    if tier == Tier.VIP:
        return Queue.VIP_QUEUE

    return Queue.FREE_QUEUE

def _get_queue_limit(tier: Tier) -> int:
    if tier == Tier.VIP:
        return VIP_QUEUE_MAX_LOAD

    return FREE_QUEUE_MAX_LOAD

def get_queue_depth(queue_name: str) -> int|None:
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

def _verify_queue_availability(queue_name: str, tier: Tier):
    queue_depth = get_queue_depth(queue_name)
    if queue_depth is None:
        raise  RedisUnavailableError(
            f"Could not verify queue availability because Redis is unavailable. queue={queue_name}"
        )

    queue_limit = _get_queue_limit(tier)
    if queue_depth >= queue_limit:
        LOAD_SHED_REQUESTS_TOTAL.labels(tier=tier, reason=f"{queue_name}_depth_exceeded").inc()
        raise QueueFullError(f"{queue_name} max load reached. depth={queue_depth}, limit={queue_limit}")

def enqueue_job(transaction: dict[str, Any]) -> QueueJob:
    tier : Tier = transaction.get("tier", Tier.Free)
    queue_name = _get_queue_name(tier)

    _verify_queue_availability(queue_name, tier)

    job = QueueJob(
        job_id = str(uuid.uuid4()),
        transaction= transaction,
        created_at= time.time(),
        tier= tier,
        retry_count= 0
    )

    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush( queue_name,job.json()),
            operation_name=f"redis_enqueue_{tier}"
        )

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_enqueue_{tier}").inc()
        logger.error(f'redis unavailable during enqueue {tier}: {e}')
        raise RedisUnavailableError(
            f"Failed to enqueue job because Redis is unavailable. tier={tier}"
        ) from e

    QUEUE_INGRESS_TOTAL.labels(tier).inc()

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
