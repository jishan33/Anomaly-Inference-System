from app.api.models.transaction import Transaction
from app.inference.configs.queue_config import Tier
from openai import BaseModel


class PredictionRequest(BaseModel):
    request_id: str
    amount: float
    tier: Tier


def to_prediction_request(transaction:Transaction, tier:Tier, job_id: str) -> PredictionRequest:
    return PredictionRequest(
        request_id = job_id,
        amount = transaction.amount,
        tier = tier
    )


class PredictionResult(BaseModel):
    request_id: str
    is_anomaly: bool
    score: float
    tier: Tier
    model_version: str
