import json
import time
from typing import List

from app.api.temp_transaction_store import redis_client
from app.model.inference import run_inference
from app.model.metrics import QUEUE_DEPTH, WORKER_PROCESSING_LATENCY, QUEUE_WAIT_TIME, PROCESSED_REQUESTS


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

        raw_job = redis_client.lpop(queue_name)

        if raw_job is None:
            # If queue is empty and we have nothing, exit immediately to avoid blocking
            if not batch:
                return []
            # If we already have items, give it a tiny break or break if timeout hit
            break

        try:
            job_data = json.loads(raw_job)
            batch.append(job_data)
        except (json.JSONDecodeError, TypeError) as e:
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
    queue_depth = redis_client.llen(queue_name)
    QUEUE_DEPTH.labels(worker_role=worker_role, tier=tier).set(queue_depth)

    if not batch:
        return False

    print(f"Executing {tier}_batch size {len(batch)}", flush=True)

    # Track queue wait times for all items in the batch
    now = time.time()
    for job in batch:
        queue_wait = now - job.get("enqueued_at", now)
        QUEUE_WAIT_TIME.labels(worker_role=worker_role, tier=tier).observe(queue_wait)

    # Extract transactions for true parallel batch inference
    transactions = [job["transaction"] for job in batch]

    ######## Future GPU work ########
    start_inference = time.time()
    results = run_inference(transactions)
    latency = time.time() - start_inference
    WORKER_PROCESSING_LATENCY.labels(worker_role=worker_role, tier=tier).observe(latency)

    # Save results back to Redis
    for job, result in zip(batch, results):
        redis_client.set(
            f"job_result:{job['job_id']}",
            json.dumps(result)
        )
        PROCESSED_REQUESTS.labels(result.tier).inc()
        print(f"Processed job {job['job_id']}")

    return True



