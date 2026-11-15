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
    (200, BatchConfig(64, 0.10)),
    (90, BatchConfig(32, 0.07)),
    (25, BatchConfig(16, 0.05)),
    (5, BatchConfig(8, 0.025)),
    (0, BatchConfig(2, 0.015))
]

# Decreasing ration adjustments during VIP queue surges
RATIO_THRESHOLDS: List[Tuple[int, float]] = [
    (170, 0.0),
    (150, 0.2),
    (130, 0.4),
    (100, 0.6),
    (80, 0.8),
    (0, 1.0)
]