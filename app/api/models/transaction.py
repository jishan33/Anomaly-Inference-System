from app.api.customer import CustomerTokenStr
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List, Annotated


TransactionTokenStr= Annotated[
    str,
    Field(
        min_length=20,
        max_length=80,
        pattern=r"^TXN_[A-Za-z0-9]{16,76}$"
    )
]


class RiskLabel(StrEnum):
    HIGH_SCAM_RISK = "HIGH_SCAM_RISK"
    POTENTIAL_SCAM = "POTENTIAL_SCAM"
    LOW_RISK = "LOW_RISK"

class Transaction(BaseModel):
    amount: float
    customer_token: CustomerTokenStr
    created_at: str
    transaction_token: TransactionTokenStr
    type: str
    is_new_destination: bool | None = None
    destination_risk_score: int | None = None
    destination_risk_signals: List[str] | None = None
    risk_label: RiskLabel | None = None
