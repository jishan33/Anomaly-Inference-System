from app.inference.config import RawJob
from app.inference.queue_service import QueueJob


def validate_queue_job(job: RawJob) -> QueueJob:

   return QueueJob.parse_raw(job)