import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from app.shared.redis import redis_client
from app.inference.config import JOB_TTL_SECONDS, MAX_JOB_RETRIES, OptionalRawJob, PredictionResult, Tier
from app.inference.clients.inference_client import process_anomaly_detection
from app.shared.metrics import QUEUE_DEPTH, WORKER_PROCESSING_LATENCY, QUEUE_WAIT_TIME, PROCESSED_REQUESTS, \
    REDIS_OPERATION_FAILURES_TOTAL, WORKER_BATCH_SIZE, WORKER_BATCH_FLUSH_TOTAL
from app.inference.queue_service import QueueJob, get_queue_depth, move_to_dlq
from app.shared.redis import redis_circuit_breaker

logger = logging.getLogger(__name__)

@dataclass
class FetchBatchResult:
    batch: list[QueueJob]
    flush_reason: str = "unknown"

def _job_to_json(job: QueueJob) -> str:
    if hasattr(job, "model_dump_json"):
        return job.model_dump_json()

    return job.json()

def _result_to_json(result: PredictionResult) -> str:
    if hasattr(result, "model_dump_json"):
        return result.model_dump_json()

    if hasattr(result, "json"):
        return result.json()

    return json.dumps(result)

def _record_batch_metrics(batch: list[QueueJob], tier: Tier, worker_role: str, flush_reason: str,) -> None:
    if not batch:
        return

    WORKER_BATCH_SIZE.labels(
        worker_role=worker_role,
        tier=tier,
        flush_reason=flush_reason
    ).observe(len(batch))

    WORKER_BATCH_FLUSH_TOTAL.labels(
        worker_role=worker_role,
        tier=tier,
        reason=flush_reason,
    ).inc()

def _parse_raw_job(raw_job: OptionalRawJob, queue_name: str) -> Optional[QueueJob]:
    try:
        return QueueJob.parse_raw(raw_job)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        move_to_dlq(raw_job, "invalid_job_payload")
        logger.warning("Failed to parse job from %s: %s", queue_name, e)
        return None

def _is_job_expired(job: QueueJob) -> bool:
    return time.time() - job.created_at > JOB_TTL_SECONDS


def _should_drop_job(job: QueueJob, raw_job: OptionalRawJob) -> bool:
    if _is_job_expired(job):
        move_to_dlq(raw_job, "job_expired")
        return True

    if job.retry_count >= MAX_JOB_RETRIES:
        move_to_dlq(raw_job, "max_retries_exceeded")
        return True

    return False

def fetch_batch(queue_name: str,
                max_batch_size: int,
                max_wait_time: float,
                poll_interval_seconds: float = 0.01,
                ) -> FetchBatchResult:

    """
    Fetches a batch of jobs from Redis.

    Flush reasons:
    - max_batch_size: batch reached configured max size
    - max_wait_time: batch waited long enough and should be processed
    - queue_empty: queue had no jobs before any batch was formed
    - redis_unavailable: Redis read failed
    """
    batch: list[QueueJob] = []
    start_monotonic = time.monotonic()

    while len(batch) < max_batch_size:
        elapse = time.monotonic() - start_monotonic

        if batch and elapse >= max_wait_time:
            return FetchBatchResult(batch=batch, flush_reason="max_wait_time")

        try:
            raw_job: OptionalRawJob = redis_circuit_breaker.call(
                lambda: redis_client.lpop(queue_name),
                operation_name="redis_lpop",
            )
        except Exception as e:
            REDIS_OPERATION_FAILURES_TOTAL.labels(
                operation="redis_lpop"
            ).inc()

            logger.warning("Redis unavailable during lpop: %s", e)
            return FetchBatchResult(batch=batch, flush_reason="redis_unavailable")

        if raw_job is None:
            if not batch:
                return FetchBatchResult(batch=batch, flush_reason="empty_queue")

            time.sleep(poll_interval_seconds)
            continue

        job = _parse_raw_job(raw_job, queue_name)
        if job is None:
            continue

        if _should_drop_job(job, raw_job):
            continue

        batch.append(job)

    return FetchBatchResult(batch=batch, flush_reason="max_batch_size")

def _update_queue_depth_metric(queue_name: str, tier: Tier, worker_role: str,) -> None:
    queue_depth: int | None = get_queue_depth(queue_name)
    QUEUE_DEPTH.labels(worker_role=worker_role, tier=tier).set(queue_depth)

def _observe_queue_wait_time( batch: list[QueueJob], tier: Tier, worker_role: str) -> None:
    now = time.time()

    for job in batch:
        queue_wait = now - job.created_at

        QUEUE_WAIT_TIME.labels(
            worker_role=worker_role,
            tier=tier,
        ).observe(queue_wait)

def _requeue_or_dlq_failed_batch(batch: list[QueueJob], queue_name: str, reason: str) -> None:
    for job in batch:
        job.retry_count += 1

        if job.retry_count >= MAX_JOB_RETRIES:
            move_to_dlq(_job_to_json(job), reason)

        try:
            redis_circuit_breaker.call(
                lambda: redis_client.rpush(queue_name, _job_to_json(job)),
                operation_name="redis_requeue",
            )

        except Exception as requeue_error:
            REDIS_OPERATION_FAILURES_TOTAL.labels(
                operation="redis_requeue",
            ).inc()

            logger.error(
                "Failed to requeue job %s: %s",
                job.job_id,
                requeue_error,
            )

def _save_result(job: QueueJob, result: PredictionResult) -> bool:
    try:
        redis_circuit_breaker.call(
            lambda: redis_client.set( f"job_result:{job.job_id}",_result_to_json(result)),
            operation_name="redis_set_result",
        )

        PROCESSED_REQUESTS.labels(
            tier=result.tier,
        ).inc()

        return True

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(
            operation="redis_set_result",
        ).inc()

        logger.error("Redis unavailable during set_result for job %s: %s", job.job_id, e)
        return False


def process_batch(
        queue_name: str,
        tier: Tier,
        max_batch_size: int,
        max_wait_time: float,
        worker_role: str,
) -> bool:

    _update_queue_depth_metric(
        queue_name=queue_name,
        tier=tier,
        worker_role=worker_role,
    )

    """
    Fetches, observes, executes, and stores results for one batch.

    Returns:
    - True if a batch was processed successfully
    - False if no work was processed or processing failed
    """
    fetch_result = fetch_batch( queue_name=queue_name, max_batch_size=max_batch_size, max_wait_time=max_wait_time )

    batch = fetch_result.batch
    if not batch:
        return False

    _record_batch_metrics(
        batch=batch,
        tier=tier,
        worker_role=worker_role,
        flush_reason=fetch_result.flush_reason,
    )
    num_jobs = len(batch)
    logger.info("Executing %s batch with size=%s, flush_reason=%s",tier,num_jobs, fetch_result.flush_reason)

    _observe_queue_wait_time(
        batch=batch,
        tier=tier,
        worker_role=worker_role,
    )

    transactions = [job.transaction for job in batch]

    start_inference = time.time()

    try:
        results: list[PredictionResult] = process_anomaly_detection(transactions)

        latency = time.time() - start_inference

        WORKER_PROCESSING_LATENCY.labels(
            worker_role=worker_role,
            tier=tier,
        ).observe(latency)

    except Exception as e:
        logger.warning("Batch inference failed for %s jobs: %s", num_jobs, e)

        _requeue_or_dlq_failed_batch(
            batch=batch,
            queue_name=queue_name,
            reason="batch_inference_failed",
        )

        return False

    if len(results) != len(batch):
        logger.error(
            "Batch result count mismatch. jobs=%s results=%s",
            len(batch),
            len(results),
        )

        for job in batch[len(results):]:
            _requeue_or_dlq_failed_batch(
                batch=[job],
                queue_name=queue_name,
                reason="missing_inference_result",
            )

    all_saved = True

    for job, result in zip(batch, results):
        saved = _save_result(job, result)
        all_saved = all_saved and saved

    return all_saved




