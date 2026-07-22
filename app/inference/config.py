from app.api.customer import CustomerTokenStr
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List, NamedTuple, Tuple



# -------------------------------------------------------------------------
# Batch Configurations & Thresholds
# -------------------------------------------------------------------------
# 1. define a clear schema for what the configuration represents
class BatchConfig(NamedTuple):
    max_batch_size: int
    max_wait_time: float

# 2. decouple the thresholds from the logic.
# Ordered from the highest threshold to lowest for easy fallback logic.
BATCH_THRESHOLDS: List[Tuple[int, BatchConfig]] = [
    (50, BatchConfig(16, 0.05)),
    (10, BatchConfig(8, 0.02)),
    (0, BatchConfig(2, 0.005))
]

# Decreasing ration adjustments during VIP queue surges
RATIO_THRESHOLDS: List[Tuple[int, float]] = [
    (130, 0.0),
    (100, 0.3),
    (80, 0.5),
    (0, 1.0)
]

#-------------------
# Queue Jobs
#-------------------
class Queue(StrEnum):
    FREE_QUEUE = "free_jobs"
    VIP_QUEUE = "vip_jobs"

FREE_QUEUE_MAX_LOAD = 1000
VIP_QUEUE_MAX_LOAD = 500

JOB_TTL_SECONDS = 30
MAX_JOB_RETRIES = 3
DEAD_LETTER_QUEUE = "dead_letter_queue"

RawJob = bytes | str
OptionalRawJob = RawJob | None

class Tier(StrEnum):
    VIP = "VIP"
    Free = "FREE"


class PredictionResult(NamedTuple):
    is_anomaly: bool
    score: float
    tier: Tier
    model_version: str


class PredictRequest(BaseModel):
    customer_token: CustomerTokenStr
    amount: float = Field(...,gt=0)
    tier: Tier
