
import json
import time
import uuid
from app.model.metrics import QUEUE_INGRESS_TOTAL

FREE_QUEUE = "free_jobs"
VIP_QUEUE = "vip_jobs"

def enqueue_job(redis_client, transaction: dict):
    job_id = str(uuid.uuid4())
    tier = transaction.get("tier")
    job = {
        "job_id": job_id,
        "transaction": transaction,
        "created_at": time.time(),
        "tier": tier,
        "retry_count": 0
    }

    if tier == "vip":
        redis_client.rpush(
            VIP_QUEUE,
            json.dumps(job)
        )
    else:
        redis_client.rpush(
            FREE_QUEUE,
            json.dumps(job)
        )

    QUEUE_INGRESS_TOTAL.labels(tier).inc()

    return job_id