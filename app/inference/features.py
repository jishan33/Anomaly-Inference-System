from typing import NamedTuple

from app.inference.config import Tier


class Features(NamedTuple):
    amount: int
    tier: Tier


def extract_features(transaction:dict) -> Features:
    """Convert raw request -> numerical feature vector"""

    amount = transaction.get("amount", 0)
    tier = transaction.get("tier", "unknown")

    # Minimal feature set (expand later)
    return Features(
        amount = amount,
        tier = tier
    )
