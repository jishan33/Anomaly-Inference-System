from enum import Enum
from typing import List, NamedTuple, Tuple, TypedDict


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



MIN_SHARED_WORKERS = 1
MAX_SHARED_WORKERS = 4

MIN_VIP_WORKERS = 2
MAX_VIP_WORKERS = 4

SCALE_UP_QUEUE_DEPTH = 20
SCALE_DOWN_QUEUE_DEPTH = 5


#-------------------
# Queue
#-------------------
FREE_QUEUE = "free_jobs"
VIP_QUEUE = "vip_jobs"

JOB_TTL_SECONDS = 30
MAX_JOB_RETRIES = 3
DEAD_LETTER_QUEUE = "dead_letter_queue"

RawJob = bytes | str
OptionalRawJob = RawJob | None

class DlqPayload(TypedDict):
    raw_job: RawJob
    reason: str
    created_at: float

class Tier(Enum):
    VIP = 1
    FREE = 2
