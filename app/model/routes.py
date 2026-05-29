import json

from fastapi import APIRouter, HTTPException

from app.shared.redis import inference_redis_client
from app.model.model import PredictRequest
from app.model.queue_service import enqueue_job
from app.shared.redis import redis_circuit_breaker

router = APIRouter()
# @router.post(path="/predict", response_model = PredictResponse)
# async def predict(req: PredictRequest):
#     result = run_inference(req.dict())
#     return result

@router.post(path="/predict_async")
async def predict_async(req: PredictRequest):
    try:
        job_id = enqueue_job(
            transaction=req.model_dump(),
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Async inference queue is temporarily unavailable"
        )

    return  {
        "job_id": job_id,
        "status": "queued",
        "tier": req.tier
    }

@router.get("/result/{job_id}")
async def get_result(job_id:str):
    try:
        result = redis_circuit_breaker.call(
            lambda: inference_redis_client.get(f"job_result:{job_id}"),
            operation_name="redis_get_result",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Result store is temporarily unavailable"
        )

    if not result:
        return {"status": "processing"}

    return json.loads(result)
