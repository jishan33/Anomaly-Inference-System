import json
from typing import Any

from pydantic import ValidationError

from app.api.customer import Customer
from app.inference.config import RawJob, PredictRequest, Tier
from app.inference.queue_service import QueueJob


def validate_queue_job(job: RawJob) -> QueueJob:
    try:
        job_data: dict[str, Any] = json.loads(job)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON payload: {e}")

    required_fields = [
        "job_id",
        "transaction",
        "created_at",
        "tier",
        "retry_count",
    ]

    for field in required_fields:
        if job_data.get(field) is None:
            raise ValueError(f"Missing required field: {field}")

    return QueueJob(
        job_id= job_data["job_id"],
        transaction=job_data["transaction"],
        created_at= job_data["created_at"],
        tier= job_data["tier"],
        retry_count= job_data["retry_count"],
    )