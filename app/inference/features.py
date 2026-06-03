from typing import NamedTuple


class Features(NamedTuple):
    amount: int
    tier: str


def extract_features(transaction:dict) -> Features:
    """Convert raw request -> numerical feature vector"""

    amount = transaction.get("amount", 0)
    tier = transaction.get("tier", "unknown")

    # Minimal feature set (expand later)
    return Features(
        amount = amount,
        tier = tier
    )
