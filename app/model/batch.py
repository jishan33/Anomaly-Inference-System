import json
import time
from typing import List

from app.api.temp_transaction_store import redis_client
from app.model.config import JOB_TTL_SECONDS, MAX_JOB_RETRIES, OptionalRawJob
from app.model.inference import run_inference
from app.shared.metrics import QUEUE_DEPTH, WORKER_PROCESSING_LATENCY, QUEUE_WAIT_TIME, PROCESSED_REQUESTS
from app.model.queue_service import QueueJob, get_queue_depth, move_to_dlq
from app.model.validate import validate_queue_job
from app.shared.redis import redis_circuit_breaker

def fetch_batch(queue_name: str, max_batch_size: int, max_wait_time: float) -> List[QueueJob]:
    """
    Safely fetches a batch of jobs from the specified Redis queue.
    Returns a list of parsed JSON dictionaries.
    """
    batch: List[QueueJob] = []
    start_time = time.time()

    while len(batch) < max_batch_size:
        # Check timeout only if we already have some items and are waiting for more
        if batch and (time.time() - start_time > max_wait_time):
            break
        # raw_job type serialized string or byte or none
        try:
            raw_job: OptionalRawJob = redis_circuit_breaker.call(
                lambda: redis_client.lpop(queue_name),
                operation_name="redis_lpop"
            )
        except Exception as e:
            print(f"Redis unavailable during lpop: {e}")
            return []

        if raw_job is None:
            # If queue is empty and we have nothing, exit immediately to avoid blocking
            if not batch:
                return []
            # If we already have items, give it a tiny break or break if timeout hit
            break

        try:
            validated_job: QueueJob = validate_queue_job(raw_job)

            created_at: float =validated_job["created_at"]
            job_age: float = time.time() - created_at
            if  job_age > JOB_TTL_SECONDS:
                move_to_dlq(raw_job, "job_expired")
                continue

            retry_count: int = validated_job["retry_count"]
            if retry_count >= MAX_JOB_RETRIES:
                move_to_dlq(raw_job, "max_retries_exceeded")
                continue


            batch.append(validated_job)

        except (json.JSONDecodeError, TypeError) as e:
            move_to_dlq(raw_job, f"invalid_job_payload:{e}")
            print(f"Failed to parse job from {queue_name}: {e}")
            continue

    return batch

def process_batch(queue_name: str, tier: str, max_batch_size: int, max_wait_time: float, worker_role: str) -> bool:
    """
    Fetches, tracks metrics for, and executes a batch of jobs.
    Returns True if work was processed, False if queue was empty.
    """
    batch = fetch_batch(queue_name, max_batch_size, max_wait_time)

    # Update queue depth metric
    queue_depth: int|None = get_queue_depth(queue_name)
    if queue_depth is not None:
        QUEUE_DEPTH.labels(worker_role=worker_role, tier=tier).set(queue_depth)
    else:
        return False


    if not batch:
        return False

    print(f"Executing {tier}_batch size {len(batch)}", flush=True)

    # Track queue wait times for all items in the batch
    now = time.time()
    for job in batch:
        queue_wait = now - job.get("created_at", now)
        QUEUE_WAIT_TIME.labels(worker_role=worker_role, tier=tier).observe(queue_wait)

    # Extract transactions for true parallel batch inference
    transactions = [job["transaction"] for job in batch]

    ######## Future GPU work ########
    start_inference = time.time()
    try:
        results = run_inference(transactions)
        latency = time.time() - start_inference
        WORKER_PROCESSING_LATENCY.labels(worker_role=worker_role, tier=tier).observe(latency)
    except Exception as e:
        for job in batch:
            job["retry_count"] = job.get("retry_count", 0) + 1
            if job["retry_count"] >= MAX_JOB_RETRIES:
                move_to_dlq(json.dumps(job), f"batch_inference_failed:{e}")
            else:
                try:
                    redis_circuit_breaker.call(
                        lambda: redis_client.rpush(queue_name, json.dumps(job)),
                        operation_name="redis_requeue"
                    )
                except Exception as requeue_error:
                    print(
                        f"Failed to requeue job "
                        f"{job.get('job_id')}: {requeue_error}"
                    )
                    continue
        return False

    # Save results back to Redis
    for job, result in zip(batch, results):
        try:
            redis_circuit_breaker.call(
                lambda: redis_client.set(f"job_result:{job['job_id']}", json.dumps(result)),
                operation_name="redis_set_result"
            )
            PROCESSED_REQUESTS.labels(result.tier).inc()
            print(f"Processed job {job['job_id']}")
        except Exception as e:
            print(f"redis unavailable during set_result: {e}")
            return False
    return True



