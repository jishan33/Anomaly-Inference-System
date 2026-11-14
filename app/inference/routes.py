from datetime import datetime, timezone
import json
import logging

from typing import List
from fastapi import APIRouter, HTTPException
from app.api.transaction import Transaction
from app.inference.clients import inference_client
from app.inference.clients.vllm_client import create_vllm_client, transaction_explainer
from app.shared.redis import redis_client
from app.inference.queue_service import enqueue_job, QueueJob, QueueFullError, RedisUnavailableError
from app.shared.redis import redis_circuit_breaker

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(path="/risk_summaries/batch")
async def risk_summaries_batch(txns: List[Transaction]):
    try:
        client = create_vllm_client()
        responses = await transaction_explainer(client, txns)
    except Exception as exc:
        logger.exception(
            "Failed to generate batch risk summaries (%s): %s",
            type(exc).__name__,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail="Failed to generate risk summaries."
        ) from exc

    return {"responses": responses }

@router.post(path="/predict_async")
async def predict_async(txn: Transaction):
    try:
        job: QueueJob = enqueue_job(
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
    return {
        "job_id": job_id,
        "customer_token": data[0],
        "transaction_token": data[1],
        "is_anomaly": data[2],
        "score": data[3],
        "tier": data[4],
        "model_version": data[5],
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