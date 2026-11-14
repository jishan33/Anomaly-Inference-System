from typing import NamedTuple, Tuple

from app.inference.queue_config import BatchConfig, BATCH_THRESHOLDS, RATIO_THRESHOLDS, Tier, QueueType
from app.inference.queue_config import Queue
from app.shared.metrics import  CURRENT_BATCH_SIZE, CURRENT_BATCH_TIMEOUT
from app.inference.queue_service import get_queue_depth, get_queue_name


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

def get_vip_batch_config(queue:Queue) -> Tuple[BatchConfig, float]:
    depth: int|None = get_queue_depth(queue)

    if depth is not None:
        config = get_batch_config(depth)
        free_batch_ratio = get_free_batch_ratio(depth)

        CURRENT_BATCH_SIZE.labels(tier= Tier.VIP, queue_name= queue).set(config.max_batch_size)
        CURRENT_BATCH_TIMEOUT.labels(tier= Tier.VIP, queue_name= queue).set(config.max_wait_time)
        return config, free_batch_ratio
    else:
        return BatchConfig(0, 0), 1

def get_free_batch_config(queue: Queue, free_batch_ratio: float) -> BatchConfig :
    depth: int|None = get_queue_depth(queue)

    if depth is not None:
        config = get_batch_config(depth)
        max_batch_size = round(free_batch_ratio * config.max_batch_size)

        CURRENT_BATCH_SIZE.labels(tier= Tier.FREE, queue_name= queue).set(max_batch_size)
        CURRENT_BATCH_TIMEOUT.labels(tier= Tier.FREE, queue_name= queue).set(config.max_wait_time)

        return BatchConfig(
            max_batch_size=max_batch_size,
            max_wait_time=config.max_wait_time
        )
    else:
        return BatchConfig(0, 0)



def get_batch_scheduler(queue_type: QueueType) -> BatchScheduler:
    vip_queue_name = get_queue_name(queue_type, Tier.VIP)
    free_queue_name = get_queue_name(queue_type, Tier.FREE)

    vip_config, free_batch_ratio = get_vip_batch_config(vip_queue_name)
    free_config = get_free_batch_config(free_queue_name, free_batch_ratio)

    return BatchScheduler(
        vip_max_batch_size= vip_config.max_batch_size,
        free_max_batch_size= free_config.max_batch_size,
        vip_max_wait_time= vip_config.max_wait_time,
        free_max_wait_time= free_config.max_wait_time
    )
