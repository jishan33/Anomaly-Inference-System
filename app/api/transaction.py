import logging
import random
import time

from app.api.customer import CustomerTokenStr, generate_exact_customer_token
from app.shared.metrics import VOLUME_GAUGE
from app.api.retry import retry_with_backoff
from app.shared.redis import redis_circuit_breaker, redis_client
from datetime import timezone
from enum import StrEnum
from faker import Faker
from pydantic import BaseModel, Field
from redis import RedisError
from typing import List, Annotated

logger = logging.getLogger(__name__)
KEY = "transactions"
WINDOW_SECONDS = 60

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

def generate_random_transaction() -> Transaction:
    fake = Faker()
    random_date_obj = fake.date_time_between(start_date='-5m', end_date='now', tzinfo=timezone.utc)
    return Transaction(
        amount=fake.pyfloat(left_digits=6, right_digits=2, positive=True, min_value=0.01),
        created_at=random_date_obj.isoformat(),
        type=random.choice(["PAYMENT", "REFUND", "TRANSFER"]),
        customer_token=generate_exact_customer_token(),
        transaction_token=f"TXN_{fake.uuid4().replace('-', '')[:26].upper()}"
    )

def append_to_redis(transactions: List[Transaction], request_id: str = "unknown"):
    def operation():
        for txn in transactions:
            now = time.time()
            # unique key for this specific transaction's details
            data_key = f"txn:{txn.transaction_token}"

            # store the full data as a Hash with an automatic 60s expiration
            redis_client.hset(data_key, mapping=txn.model_dump())
            redis_client.expire(data_key, WINDOW_SECONDS)

            # Global SET
            # add to the Global Sorted Set (The index for get_volume)
            # Member: transaction_token, Score: current timestamp
            redis_client.zadd(KEY, {txn.transaction_token: now})

            # Per-customer SET (needed for rate-limiting)
            customer_index_key = f"customer_index:{txn.customer_token}"
            redis_client.zadd(customer_index_key, {txn.transaction_token: now})
            redis_client.zremrangebyscore(customer_index_key, 0, now - WINDOW_SECONDS)

        # clean up the sorted set index (Removes tokens older than 60s)
        redis_client.zremrangebyscore(KEY, 0, time.time() - WINDOW_SECONDS)

    try:
        redis_circuit_breaker.call(
            lambda :retry_with_backoff(operation, operation_name="append_to_redis"),
            operation_name="append_to_redis",
            request_id= request_id
        )
        VOLUME_GAUGE.inc()
    except RedisError as e:
        logger.error(
            "redis_error",
            extra={
                "extra_data": {
                    "operation": "append_to_redis",
                    "request_id": request_id,
                    "error": str(e)
                }
            }
        )

def get_volume(request_id: str):
    """Returns total transaction count across all customers in the last 60s."""
    now = time.time()

    def operation():
        return redis_client.zcount(KEY, now - WINDOW_SECONDS, now)

    try:
        return redis_circuit_breaker.call(
            lambda: retry_with_backoff(operation, operation_name="get_volume"),
            operation_name="get_volume",
            request_id= request_id
        )
    except Exception as e:
        logger.error(
            "redis_error",
            extra={
                "extra_data": {
                    "operation": "get_volume",
                    "request_id": request_id,
                    "error": str(e)
                }
            }
        )
        return 0

def get_customer_transaction_volume(customer_token: CustomerTokenStr, request_id: str):
    """To get a SPECIFIC customer's volume, we need a per-customer Sorted Set"""
    customer_index_key = f"customer_index:{customer_token}"
    now = time.time()

    def operation():
        return redis_client.zcount(customer_index_key, now - WINDOW_SECONDS, now)

    try:
        return redis_circuit_breaker.call(
            lambda: retry_with_backoff(operation, operation_name="get_customer_transaction_volume"),
            operation_name="get_customer_transaction_volume",
            request_id= request_id
        )
    except Exception as e:
        logger.error(
            "redis_error",
            extra={
                "extra_data": {
                    "operation": "get_customer_transaction_volume",
                    "request_id": request_id,
                    "customer_token": customer_token,
                    "error": str(e)
                }
            }
        )
        return 0

# ------------------------
# Safe wrappers
# ------------------------
def safe_get_volume(request_id: str = "unknown") -> int:
    try:
        return get_volume(request_id)
    except Exception:
        return 0

def safe_get_customer_transaction_volume(customer_token: CustomerTokenStr, request_id: str = "unknown") -> int:
    try:
        return get_customer_transaction_volume(customer_token, request_id)
    except Exception:
        return 0


DESTINATION_RISK_SCENARIOS = [
    (0, 1, []),
    (2, 5, ["Destination has one unresolved scam report."]),
    (6, 10, ["Destination is linked to multiple prior scam reports."]),
]
def generate_risk_evaluated_transaction() -> Transaction:
    txn = generate_random_transaction()
    is_new_destination = random.choice((True, False))
    risk_score = random.randint(0, 10)

    if risk_score < 2:
        risk_label = RiskLabel.LOW_RISK
        signals = []
    elif risk_score <= 5:
        risk_label = RiskLabel.POTENTIAL_SCAM
        signals = [random.choice((
            "The destination has one unresolved scam report.",
            "The destination matches an account on a synthetic watchlist.",
        ))]
    else:
        risk_label = RiskLabel.HIGH_SCAM_RISK
        signals = [random.choice((
            "The destination is linked to multiple prior scam reports.",
            "The destination matches an account blocked in a prior scam case.",
        ))]

    txn.is_new_destination = is_new_destination
    txn.destination_risk_score = risk_score
    txn.risk_label = risk_label
    txn.destination_risk_signals = signals

    return txn
