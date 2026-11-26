
import json
import logging
import random
import time
import uuid
from typing import Callable

from app.api.models.transaction import Transaction
from app.inference.models.risk_summary_model import RiskSummaryResponse
from app.inference.models.prediction_model import PredictionResult
from app.inference.models.queue_job_model import QueueJob, DlqPayload, QueueFullError, \
    RedisUnavailableError
from app.inference.configs.queue_config import get_queue_name, Queue, RawJob, DEAD_LETTER_QUEUE, Tier, \
    VIP_QUEUE_MAX_LOAD, \
    FREE_QUEUE_MAX_LOAD, QueueType, MAX_JOB_RETRIES
from app.shared.metrics import QUEUE_INGRESS_TOTAL, DEAD_LETTER_QUEUE_JOBS_TOTAL, DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL, \
    DLQ_PUSH_FAILURE_TOTAL, REDIS_OPERATION_FAILURES_TOTAL, LOAD_SHED_REQUESTS_TOTAL, PROCESSED_REQUESTS
from app.shared.redis import redis_circuit_breaker, redis_client

logger = logging.getLogger(__name__)

def get_queue_depth(queue_name: Queue) -> int|None:
    try:
        queue_depth: int = redis_circuit_breaker.call(
            lambda: redis_client.llen(queue_name),
            operation_name=f"redis_llen_{queue_name}"
        )
        return queue_depth

    except Exception as e:
        record_metric_safely(lambda: REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_llen_{queue_name}").inc())

        logger.exception("Redis unavailable for LLEN operation on %s: %s", queue_name, e)
        return None

def _get_queue_limit(tier: Tier) -> int:
    if tier == Tier.VIP:
        return VIP_QUEUE_MAX_LOAD

    return FREE_QUEUE_MAX_LOAD

def _verify_queue_availability(queue_name: Queue, tier: Tier):
    queue_depth = get_queue_depth(queue_name)

    if queue_depth is None:
        raise  RedisUnavailableError(
            f"Could not verify queue availability because Redis is unavailable. queue={queue_name}"
        )

    queue_limit = _get_queue_limit(tier)

    if queue_depth >= queue_limit:
        record_metric_safely(lambda: LOAD_SHED_REQUESTS_TOTAL.labels(tier=tier, reason=f"{queue_name}_depth_exceeded").inc())

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
        record_metric_safely(lambda: REDIS_OPERATION_FAILURES_TOTAL.labels(operation=f"redis_enqueue_{queue_name}").inc())
        logger.exception(f'redis unavailable during enqueue {queue_name} job: {e}')

        raise RedisUnavailableError(
            f"Failed to enqueue {queue_name} job because Redis is unavailable."
        ) from e

    else:
        record_metric_safely(
            lambda: QUEUE_INGRESS_TOTAL.labels(
                queue_name=queue_name,
                tier= tier,
                queue_type= queue_type,
            ).inc()
        )

    return job

def _build_job_result(job: QueueJob, result: PredictionResult | RiskSummaryResponse) -> dict:
    return {
        "job": job.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
     }

def save_result(job: QueueJob, result: PredictionResult | RiskSummaryResponse, queue_name: Queue) -> bool:
    try:
        job_result: dict = _build_job_result(job, result)
        payload = json.dumps(job_result)

        redis_circuit_breaker.call(
            lambda: redis_client.set(
                f"job_result:{job.job_id}", payload),
            operation_name="redis_set_result",
        )

    except Exception as e:
        requeue_or_dlq_failed_batch([job], queue_name, "failed_to_save_result")

        record_metric_safely(
            lambda: REDIS_OPERATION_FAILURES_TOTAL.labels(
            operation="redis_set_result",
            ).inc()
        )

        logger.error("Redis unavailable during set_result for job %s: %s", job.job_id, e)
        return False

    else:
        record_metric_safely(
            lambda: PROCESSED_REQUESTS.labels(
                tier=job.tier,
                queue_type=job.queue_type,
            ).inc()
        )
        return True

def move_to_dlq(raw_job: RawJob, reason: str) -> bool:
    dlq_payload = DlqPayload(
        raw_job= raw_job.decode() if isinstance(raw_job, bytes) else raw_job,
        reason= reason,
        failed_at= time.time()
    )

    record_metric_safely(
        lambda: DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL.labels(reason=reason).inc()
    )

    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush(DEAD_LETTER_QUEUE, json.dumps(dlq_payload)),
            operation_name= "redis_dlq_push"
        )

    except Exception as e:
        record_metric_safely(lambda: DLQ_PUSH_FAILURE_TOTAL.labels(reason=reason).inc())
        record_metric_safely(lambda: REDIS_OPERATION_FAILURES_TOTAL.labels(operation="redis_dlq_push").inc())

        logger.exception(
            f"CRITICAL: failed to move job to DLQ. "
            f"reason={reason}, error={e}, raw_job={raw_job}"
        )
        return False

    else:
        record_metric_safely(lambda: DEAD_LETTER_QUEUE_JOBS_TOTAL.labels(reason=reason).inc())
        logger.info(f"Moved job to DLQ. reason={reason}")
        return True

def requeue_or_dlq_failed_batch(batch: list[QueueJob], queue_name: str, reason: str) -> None:
    for job in batch:
        job.retry_count += 1

        if job.retry_count >= MAX_JOB_RETRIES:
            move_to_dlq(job.model_dump_json(), reason)

        try:
            redis_circuit_breaker.call(
                lambda: redis_client.rpush(queue_name, job.model_dump_json()),
                operation_name="redis_requeue",
            )

        except Exception as requeue_error:
            record_metric_safely(lambda:  REDIS_OPERATION_FAILURES_TOTAL.labels(operation="redis_requeue").inc())

            logger.exception(
                "Failed to requeue job %s: %s",
                job.job_id,
                requeue_error,
            )


def record_metric_safely(record: Callable[[], None]) -> None:
    try:
        record()
    except Exception:
        logger.exception("Failed to record metric")
