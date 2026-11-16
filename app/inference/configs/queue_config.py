from enum import StrEnum

#-------------------
# Queue Jobs
#-------------------
class Queue(StrEnum):
    ANOMALY_PREDICT_FREE_QUEUE = "anomaly_predict_free_jobs"
    ANOMALY_PREDICT_VIP_QUEUE = "anomaly_predict_vip_jobs"
    RISK_SUMMARY_FREE_QUEUE = "risk_summary_free_jobs"
    RISK_SUMMARY_VIP_QUEUE = "risk_summary_vip_jobs"

FREE_QUEUE_MAX_LOAD = 3000
VIP_QUEUE_MAX_LOAD = 3000

JOB_TTL_SECONDS = 30
MAX_JOB_RETRIES = 3
DEAD_LETTER_QUEUE = "dead_letter_queue"

RawJob = bytes | str
OptionalRawJob = RawJob | None

class Tier(StrEnum):
    VIP = "VIP"
    FREE = "FREE"

class QueueType(StrEnum):
    ANOMALY_PREDICT = "ANOMALY_PREDICT"
    RISK_SUMMARY = "RISK_SUMMARY"


def get_queue_name(queue_type: QueueType, tier: Tier) -> Queue:
    _QUEUE_NAMES: dict[tuple[QueueType, Tier], Queue] = {
        (QueueType.ANOMALY_PREDICT, Tier.VIP): Queue.ANOMALY_PREDICT_VIP_QUEUE,
        (QueueType.ANOMALY_PREDICT, Tier.FREE): Queue.ANOMALY_PREDICT_FREE_QUEUE,
        (QueueType.RISK_SUMMARY, Tier.VIP): Queue.RISK_SUMMARY_VIP_QUEUE,
        (QueueType.RISK_SUMMARY, Tier.FREE): Queue.RISK_SUMMARY_FREE_QUEUE,
    }
    return _QUEUE_NAMES[(queue_type, tier)]
