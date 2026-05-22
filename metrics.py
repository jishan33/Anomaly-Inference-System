from prometheus_client import Counter, Histogram, Gauge

# ------------------------
# Request Metrics
# ------------------------
REQUEST_COUNT = Counter(
    "fastapi_request_count_total",
    "Total number of requests processed",
    ["instance", "method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "fastapi_request_latency_seconds",
    "Request latency in seconds",
    ["instance", "method", "endpoint"]
)

# ------------------------
# Error Metrics
# ------------------------
ERROR_COUNT = Counter(
    "app_errors_total",
    "Total number of errors",
    ["instance","type", "status", "endpoint"]
)

# ------------------------
# Anomaly / Business Metrics
# ------------------------
ANOMALY_COUNT = Counter(
    "anomaly_detected_total",
    "Total number of detected anomalies",
    ["instance", "type"]  # type user, volume, transaction
)

USER_RATE_LIMIT = Gauge(
    "user_rate_limited_total",
    "Number of users rate-limited in last minute",
    ["instance"]
)

VOLUME_GAUGE = Gauge(
    "transaction_volume_last_minute",
    "Number of transactions processed in the last minute",
    ["instance"]
)

# ------------------------
# Optional: circuit breaker metrics
# ------------------------
CIRCUIT_BREAKER_STATE = Gauge(
    "redis_circuit_breaker_state",
    "State of Redis Circuit Breaker: 0=CLOSED, 1=OPEN, 2=HALF_OPEN",
    ["instance", "operation"]
)

# Retry metrics
RETRY_COUNT = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["instance", "operation"]
)
