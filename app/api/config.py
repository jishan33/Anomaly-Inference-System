import json
import os
import logging
from datetime import datetime, timezone

### “Each customer can only make N requests per minute” ###

# instance id (set via env in docker-compose)
INSTANCE_ID = os.getenv("INSTANCE_ID", "local")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

NORMAL_MIN = 10
NORMAL_MAX = 100
NORMAL_VOLUME_MIN = 10
NORMAL_VOLUME_MAX = 100
NORMAL_CUSTOMER_TRANSACTION_VOLUME_MIN = 1
NORMAL_CUSTOMER_TRANSACTION_VOLUME_MAX = 10

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "instance_id": INSTANCE_ID,
        }

        # Include extra fields if present
        if hasattr(record, "extra_data"):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

class PrettyFormatter(logging.Formatter):
    def format(self, record):
        base = f"{datetime.now(timezone.utc).isoformat()} | {record.levelname} | {record.name}"

        msg = record.getMessage()

        if hasattr(record, "extra_data"):
            extra = " | ".join(f"{k}={v}" for k, v in record.extra_data.items())
            return f"{base} | {msg} | {extra}"

        return f"{base} | {msg}"

def setup_logging():
    # 🔥 IMPORTANT
    logging.getLogger("uvicorn.access").disabled = True

    handler = logging.StreamHandler()

    if LOG_FORMAT == "pretty":
        handler.setFormatter(PrettyFormatter())
    else:
        handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear existing handlers (important)
    root_logger.handlers = []
    root_logger.addHandler(handler)

