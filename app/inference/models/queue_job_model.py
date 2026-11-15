from typing import TypedDict
from pydantic import BaseModel

from app.api.transaction import Transaction
from app.inference.configs.queue_config import Tier, QueueType, RawJob, Queue


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


class QueueFullError(Exception):
    """Raised when a queue has reached its configured admission limit."""

class RedisUnavailableError(Exception):
    """Raised when Redis cannot be reached or a Redis operation fails."""
