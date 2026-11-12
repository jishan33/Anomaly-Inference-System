from typing import NamedTuple

from app.api.customer import CustomerTokenStr
from app.api.transaction import TransactionTokenStr
from app.inference.config import Tier


class Features(NamedTuple):
    customer_token: CustomerTokenStr
    transaction_token: TransactionTokenStr
    amount: int
    tier: Tier


def extract_features(transaction:dict) -> Features:
    """Convert raw request -> numerical feature vector"""
    customer_token = transaction.get("customer_token")
    transaction_token = transaction.get("transaction_token")
    amount = transaction.get("amount", 0)
    tier = transaction.get("tier", "unknown")

    # Minimal feature set (expand later)
    return Features(
        customer_token = customer_token,
        transaction_token = transaction_token,
        amount = amount,
        tier = tier
    )
