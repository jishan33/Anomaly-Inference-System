import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from app.api.transaction import Transaction
from app.inference.clients.vllm_client import transaction_explainer, create_vllm_client, ExplanationResponse
from app.shared.redis import redis_client
from app.inference.queue_config import JOB_TTL_SECONDS, MAX_JOB_RETRIES, OptionalRawJob, Tier, Queue
from app.inference.prediction_models import PredictionResult
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

def _record_batch_metrics(batch: list[QueueJob], tier: Tier, worker_role: str, queue_name: str,flush_reason: str,) -> None:
    if not batch:
        return

    WORKER_BATCH_SIZE.labels(
        worker_role=worker_role,
        tier=tier,
        queue_name =queue_name,
        flush_reason=flush_reason
    ).observe(len(batch))

    WORKER_BATCH_FLUSH_TOTAL.labels(
        worker_role=worker_role,
        tier=tier,
        queue_name =queue_name,
        reason=flush_reason,
    ).inc()

def _parse_raw_job(raw_job: OptionalRawJob, queue_name: str) -> Optional[QueueJob]:
    try:
        return QueueJob.model_validate_json(raw_job)
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

def fetch_batch(queue_name: Queue,
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

def _update_queue_depth_metric(queue_name: Queue, tier: Tier, worker_role: str,) -> None:
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
            move_to_dlq(job.model_dump_json(), reason)

        try:
            redis_circuit_breaker.call(
                lambda: redis_client.rpush(queue_name, job.model_dump_json()),
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

def _save_result(job: QueueJob, result: PredictionResult | ExplanationResponse) -> bool:
    try:
        redis_circuit_breaker.call(
            lambda: redis_client.set( f"job_result:{job.job_id}", result.model_dump_json()),
            operation_name="redis_set_result",
        )

        PROCESSED_REQUESTS.labels(
            tier=job.tier,
            queue_type = job.queue_type,
        ).inc()

        return True

    except Exception as e:
        REDIS_OPERATION_FAILURES_TOTAL.labels(
            operation="redis_set_result",
        ).inc()

        logger.error("Redis unavailable during set_result for job %s: %s", job.job_id, e)
        return False


async def process_batch(
        queue_name: Queue,
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
    fetch_result = fetch_batch(queue_name=queue_name, max_batch_size=max_batch_size, max_wait_time=max_wait_time )

    batch = fetch_result.batch
    if not batch:
        return False

    _record_batch_metrics(
        batch=batch,
        tier=tier,
        worker_role=worker_role,
        queue_name = queue_name,
        flush_reason=fetch_result.flush_reason,
    )
    num_jobs = len(batch)
    logger.info("Executing %s batch with size=%s, flush_reason=%s",tier,num_jobs, fetch_result.flush_reason)

    _observe_queue_wait_time(
        batch=batch,
        tier=tier,
        worker_role=worker_role,
    )

    transactions: list[Transaction] = [job.request for job in batch]

    start_inference = time.time()

    try:
        results: list[PredictionResult] | list[ExplanationResponse] = await determine_workload_processor(queue_name, transactions, tier)

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


async def determine_workload_processor(queue_name: Queue, transactions: list[Transaction], tier:Tier) -> list[PredictionResult] | list[ExplanationResponse]:
    if queue_name in (Queue.ANOMALY_PREDICT_VIP_QUEUE, Queue.ANOMALY_PREDICT_FREE_QUEUE):
        return process_anomaly_detection(transactions, tier)

    if queue_name in (Queue.RISK_SUMMARY_VIP_QUEUE, Queue.RISK_SUMMARY_FREE_QUEUE):
        clent = create_vllm_client()
        return await transaction_explainer(clent, transactions)

    raise RuntimeError(f"No workload processor for queue {queue_name!r}")