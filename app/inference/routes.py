from datetime import datetime, timezone
import json
import logging

from app.api.transaction import Transaction
from app.inference.clients import triton_client
from app.inference.configs.queue_config import QueueType
from app.inference.queue_service import enqueue_job
from app.inference.models.queue_job_model import QueueJob, QueueFullError, RedisUnavailableError
from app.shared.redis import redis_client, redis_circuit_breaker
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(path="/risk_summary/async")
async def risk_summary_async(txn: Transaction):
    try:
        job =  enqueue_job(
            queue_type= QueueType.RISK_SUMMARY,
            request= txn.model_dump()
        )
    except QueueFullError as e:
        raise HTTPException(status_code=429, detail=str(e))

    except RedisUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception:
        logger.exception("Unexpected enqueue failure")
        raise HTTPException(status_code=503, detail="Failed to enqueue job")

    created_at = job.created_at
    created_at_utc = datetime.fromtimestamp(created_at, tz=timezone.utc)

    return  {
        "job_id": job.job_id,
        "queue_type": job.queue_type,
        "status": "queued",
        "tier": job.tier,
        "created_at": created_at_utc
    }

@router.post(path="/predict_async")
async def predict_async(txn: Transaction):
    try:
        job: QueueJob = enqueue_job(
            queue_type= QueueType.ANOMALY_PREDICT,
            request=txn.model_dump(),
        )

    except QueueFullError as e:
        raise HTTPException(status_code=429, detail=str(e))

    except RedisUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))

    except Exception:
        logger.exception("Unexpected enqueue failure")
        raise HTTPException(status_code=503, detail="Failed to enqueue job")

    created_at = job.created_at
    created_at_utc = datetime.fromtimestamp(created_at, tz=timezone.utc)

    return  {
        "job_id": job.job_id,
        "queue_type": job.queue_type,
        "status": "queued",
        "tier": job.tier,
        "created_at": created_at_utc
    }

@router.get("/result/{job_id}")
async def get_result(job_id:str):
    try:
        result = redis_circuit_breaker.call(
            lambda: redis_client.get(f"job_result:{job_id}"),
            operation_name="redis_get_result",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Result store is temporarily unavailable"
        )

    if not result:
        return {"status": "processing"}

    data =  json.loads(result)

    return data

@router.get("/model_metadata")
async def get_model_metadata():
    try:
        result = inference_client.get_model_metadata()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail= "model metadata is unavailable"
        )

    if not result:
        return {"unavailable"}
    return result