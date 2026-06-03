from typing import NamedTuple, Tuple

from app.inference.config import BatchConfig, BATCH_THRESHOLDS, RATIO_THRESHOLDS
from app.inference.config import FREE_QUEUE, VIP_QUEUE
from app.shared.metrics import  CURRENT_BATCH_SIZE, CURRENT_BATCH_TIMEOUT
from app.inference.queue_service import get_queue_depth


class BatchScheduler(NamedTuple):
    vip_max_batch_size: int
    free_max_batch_size: int
    vip_max_wait_time: float
    free_max_wait_time: float


def get_batch_config(queue_depth: int) -> BatchConfig:
    for threshold, config in BATCH_THRESHOLDS:
        if queue_depth >= threshold:
            return config

    return BATCH_THRESHOLDS[-1][1]

def get_free_batch_ratio(vip_depth: int) -> float :
    # VIP Overload Protection Mode
    for threshold, ratio in RATIO_THRESHOLDS:
        if vip_depth >= threshold:
            return ratio
    return 1.0

def get_vip_batch_config() -> Tuple[BatchConfig, float] :
    vip_depth: int|None = get_queue_depth(VIP_QUEUE)

    if vip_depth is not None:
        vip_config = get_batch_config(vip_depth)
        free_batch_ratio = get_free_batch_ratio(vip_depth)
        CURRENT_BATCH_SIZE.labels("vip").set(vip_config.max_batch_size)
        CURRENT_BATCH_TIMEOUT.labels("vip").set(vip_config.max_wait_time)
        return vip_config, free_batch_ratio
    else:
        return BatchConfig(0, 0), 1

def get_free_batch_config(free_batch_ratio: float) -> BatchConfig :
    free_depth: int|None = get_queue_depth(FREE_QUEUE)

    if free_depth is not None:
        free_config = get_batch_config(free_depth)
        free_max_batch_size = round(free_batch_ratio * free_config.max_batch_size)

        CURRENT_BATCH_SIZE.labels("free").set(free_max_batch_size)
        CURRENT_BATCH_TIMEOUT.labels("free").set(free_config.max_wait_time)
        return BatchConfig(
            max_batch_size=free_max_batch_size,
            max_wait_time=free_config.max_wait_time
        )
    else:
        return BatchConfig(0, 0)



def get_batch_scheduler() -> BatchScheduler:
    vip_config, free_batch_ratio = get_vip_batch_config()
    free_config = get_free_batch_config(free_batch_ratio)
    return BatchScheduler(
        vip_max_batch_size= vip_config.max_batch_size,
        free_max_batch_size= free_config.max_batch_size,
        vip_max_wait_time= vip_config.max_wait_time,
        free_max_wait_time= free_config.max_wait_time
    )
