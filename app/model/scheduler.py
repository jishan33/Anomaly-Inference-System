from typing import NamedTuple

from app.model.config import BatchConfig, BATCH_THRESHOLDS, RATIO_THRESHOLDS
from app.model.config import FREE_QUEUE, VIP_QUEUE
from app.model.metrics import  CURRENT_BATCH_SIZE, CURRENT_BATCH_TIMEOUT
from app.api.temp_transaction_store import redis_client


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

def get_batch_scheduler() -> BatchScheduler:
    vip_depth = redis_client.llen(VIP_QUEUE)
    vip_config = get_batch_config(vip_depth)
    CURRENT_BATCH_SIZE.labels("vip").set(vip_config.max_batch_size)
    CURRENT_BATCH_TIMEOUT.labels("vip").set(vip_config.max_wait_time)

    free_depth = redis_client.llen(FREE_QUEUE)
    free_batch_ratio = get_free_batch_ratio(vip_depth)
    free_config = get_batch_config(free_depth)
    free_max_batch_size = round(free_batch_ratio * free_config.max_batch_size)

    CURRENT_BATCH_SIZE.labels("free").set(free_max_batch_size)
    CURRENT_BATCH_TIMEOUT.labels("free").set(free_config.max_wait_time)
    return BatchScheduler(
        vip_max_batch_size= vip_config.max_batch_size,
        free_max_batch_size= free_max_batch_size,
        vip_max_wait_time= vip_config.max_wait_time,
        free_max_wait_time= free_config.max_wait_time
    )
