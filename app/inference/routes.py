from datetime import datetime, timezone
import json
import logging

from fastapi import APIRouter, HTTPException
from app.inference.clients import inference_client
from app.shared.redis import redis_client
from app.inference.config import PredictRequest
from app.inference.queue_service import enqueue_job, QueueJob
from app.shared.redis import redis_circuit_breaker

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(path="/predict_async")
async def predict_async(req: PredictRequest):
    try:
        job: QueueJob = enqueue_job(
            transaction=req.model_dump(),
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Async inference queue is temporarily unavailable"
        )
    created_at = job.get("created_at")
    created_at_utc = datetime.fromtimestamp(created_at, tz=timezone.utc)

    return  {
        "job_id": job.get("job_id"),
        "status": "queued",
        "tier": job.get("tier"),
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
    return {
        "is_anomaly": data[0],
        "score": data[1],
        "tier": data[2],
        "model_version": data[3],
    }


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