from app.api import config
from app.api.transaction_store import Transaction

# ------------------------
# Anomaly logic
# ------------------------
def anomaly_score(transaction: Transaction):
    amount = transaction.amount
    if config.NORMAL_MIN <= amount <= config.NORMAL_MAX:
        return 0.1

    if amount < config.NORMAL_MIN:
        deviation = config.NORMAL_MIN - amount
    else:
        deviation = amount - config.NORMAL_MAX

    score = min(1.0, deviation / config.NORMAL_MAX)
    return round(score, 2)

def anomaly_volume_score(volume: int):
    if config.NORMAL_VOLUME_MIN <= volume <= config.NORMAL_VOLUME_MAX:
        return 0.1
    if volume < config.NORMAL_VOLUME_MIN:
        deviation = config.NORMAL_VOLUME_MIN - volume
    else:
        deviation = volume - config.NORMAL_VOLUME_MAX

    score = min(1.0, deviation / config.NORMAL_VOLUME_MAX)
    return round(score, 2)

def anomaly_customer_transaction_volume_score(volume: int):
    if config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN <= volume <= config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX:
        return 0.1
    if volume < config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN:
        deviation = config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN - volume
    else:
        deviation = volume - config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX

    score = min(1.0, deviation / config.NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX)
    return round(score, 2)