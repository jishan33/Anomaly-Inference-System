from typing import List

from openai import BaseModel

from app.api.transaction import Transaction, RiskLabel


class RiskSummaryRequest(BaseModel):
    amount: float
    created_at: str
    request_id: str
    type: str
    is_new_destination: bool | None = None
    destination_risk_score: int | None = None
    destination_risk_signals: List[str] | None = None
    risk_label: RiskLabel | None = None

def to_risk_summary_requests(transactions_with_job_ids: list[tuple[Transaction, str]]) -> list[RiskSummaryRequest]:
  return [
    RiskSummaryRequest(
        amount= transaction.amount,
        created_at= transaction.created_at,
        request_id = job_id,
        type= transaction.type,
        is_new_destination=transaction.is_new_destination,
        destination_risk_score=transaction.destination_risk_score,
        destination_risk_signals=transaction.destination_risk_signals,
        risk_label=transaction.risk_label
    )
    for transaction, job_id in transactions_with_job_ids
  ]