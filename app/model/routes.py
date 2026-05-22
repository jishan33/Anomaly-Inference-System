import json
from fastapi import APIRouter
from app.model.model import PredictRequest
from app.model.queue_service import enqueue_job
from temp_transaction_store import redis_client

router = APIRouter()
# @router.post(path="/predict", response_model = PredictResponse)
# async def predict(req: PredictRequest):
#     result = run_inference(req.dict())
#     return result

@router.post(path="/predict_async")
async def predict_async(req: PredictRequest):
    job_id = enqueue_job(
        redis_client=redis_client,
        transaction=req.model_dump(),
    )

    return  {
        "job_id": job_id,
        "status": "queued",
        "tier": req.tier
    }

@router.get("/result/{job_id}")
async def get_result(job_id:str):
    result = redis_client.get(
        f"job_result:{job_id}"
    )

    if not result:
        return { "status":"processing"}

    return json.loads(result)
