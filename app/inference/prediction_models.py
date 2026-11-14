from app.api.customer import CustomerTokenStr
from app.api.transaction import TransactionTokenStr, Transaction
from app.inference.queue_config import Tier
from openai import BaseModel


class PredictionRequest(BaseModel):
    customer_token: CustomerTokenStr
    transaction_token: TransactionTokenStr
    amount: float
    tier: Tier


def to_prediction_request(transaction:Transaction, tier:Tier) -> PredictionRequest:
    return PredictionRequest(
        customer_token = transaction.customer_token,
        transaction_token = transaction.transaction_token,
        amount = transaction.amount,
        tier = tier
    )


class PredictionResult(BaseModel):
    customer_token: CustomerTokenStr
    transaction_token: TransactionTokenStr
    is_anomaly: bool
    score: float
    tier: Tier
    model_version: str
