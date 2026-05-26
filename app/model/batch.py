import json
import time
from typing import List

from app.api.temp_transaction_store import redis_client
from app.model.config import JOB_TTL_SECONDS, DEAD_LETTER_QUEUE, MAX_JOB_RETRIES
from app.model.inference import run_inference
from app.model.metrics import QUEUE_DEPTH, WORKER_PROCESSING_LATENCY, QUEUE_WAIT_TIME, PROCESSED_REQUESTS
from app.shared.redis import redis_circuit_breaker

RowJob = bytes | str

def move_to_dlq(raw_job: object, reason: str) -> bool:
    dlq_payload = {
        "raw_job": raw_job.decode() if isinstance(raw_job, bytes) else raw_job,
        "reason": reason,
        "failed_at": time.time(),
    }
    try:
        redis_circuit_breaker.call(
            lambda : redis_client.rpush(DEAD_LETTER_QUEUE, json.dumps(dlq_payload)),
            operation_name= "redis_dlq_push"
        )
        print(f"Moved job to DLQ. reason={reason}")
        return True
    except Exception as e:
        print(
            f"CRITICAL: failed to move job to DLQ. "
            f"reason={reason}, error={e}, raw_job={raw_job}"
        )
        return False

def fetch_batch(queue_name: str, max_batch_size: int, max_wait_time: float) -> List[dict]:
    """
    Safely fetches a batch of jobs from the specified Redis queue.
    Returns a list of parsed JSON dictionaries.
    """
    batch = []
    start_time = time.time()

    while len(batch) < max_batch_size:
        # Check timeout only if we already have some items and are waiting for more
        if batch and (time.time() - start_time > max_wait_time):
            break
        # raw_job type serialized string or byte or none
        try:
            raw_job = redis_circuit_breaker.call(
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
            # job_data type is a dictionary
            job_data = json.loads(raw_job)


            created_at =job_data.get("created_at")
            if created_at is None:
                move_to_dlq(raw_job, "missing_created_at")
                continue

            job_age = time.time() - created_at
            if  job_age > JOB_TTL_SECONDS:
                move_to_dlq(raw_job, "job_expired")
                continue

            retry_count = job_data.get("retry_count", 0)
            if retry_count >= MAX_JOB_RETRIES:
                move_to_dlq(raw_job, "max_retries_exceeded")
                continue


            batch.append(job_data)

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
    try:
        # Update queue depth metric
        queue_depth = redis_circuit_breaker.call(
            lambda : redis_client.llen(queue_name),
            operation_name="redis_llen"
        )
        QUEUE_DEPTH.labels(worker_role=worker_role, tier=tier).set(queue_depth)
    except Exception as e:
        print(f"redis unavailable during llen: {e}")
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
                    return False
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



