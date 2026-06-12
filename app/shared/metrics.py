from prometheus_client import Counter, Histogram, Gauge

# ------------------------
# Request Metrics
# ------------------------
REQUEST_COUNT = Counter(
    "fastapi_request_count_total",
    "Total number of requests processed",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "fastapi_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"]
)

# ------------------------
# Error Metrics
# ------------------------
ERROR_COUNT = Counter(
    "app_errors_total",
    "Total number of errors",
    ["type", "status", "endpoint"]
)

# ------------------------
# Anomaly / Business Metrics
# ------------------------
ANOMALY_COUNT = Counter(
    "anomaly_detected_total",
    "Total number of detected anomalies",
    ["type"]  # type user, volume, transaction
)

USER_RATE_LIMIT = Gauge(
    "user_rate_limited_total",
    "Number of users rate-limited in last minute",
)

VOLUME_GAUGE = Gauge(
    "transaction_volume_last_minute",
    "Number of transactions processed in the last minute",
)

# ------------------------
# Optional: circuit breaker metrics
# ------------------------
CIRCUIT_BREAKER_STATE = Gauge(
    "redis_circuit_breaker_state",
    "State of Redis Circuit Breaker: 0=CLOSED, 1=OPEN, 2=HALF_OPEN",
    ["operation"]
)

# Retry metrics
RETRY_COUNT = Counter(
    "retry_attempts_total",
    "Total retry attempts",
    ["operation"]
)


# Queue depth
QUEUE_DEPTH = Gauge(
    "inference_queue_depth",
    "Number of jobs waiting in inference queue",
    ["worker_role", "tier"]

)

WORKER_PROCESSING_LATENCY = Histogram(
    "worker_processing_latency_seconds",
    "Time spent processing inference jobs",
    ["worker_role", "tier"]

)

QUEUE_WAIT_TIME = Histogram(
    "queue_wait_latency_seconds",
    "Time spent on queue waiting",
    ["worker_role", "tier"]
)

CURRENT_BATCH_SIZE = Gauge(
    "current_batch_size",
    "Current adaptive batch size",
    ["tier"]
)

CURRENT_BATCH_TIMEOUT = Gauge(
    "current_batch_timeout_seconds",
    "Current adaptive batch timeout",
    ["tier"]
)

PROCESSED_REQUESTS = Counter(
    "processed_requests_total",
    "Total processed inference requests",
    ["tier"]
)

QUEUE_INGRESS_TOTAL = Counter(
    "queue_ingress_total",
    "Total number of ingress requests added to the queue",
    ["tier"]
)

ACTIVE_WORKERS = Gauge(
    "active_workers",
    "Currently active workers",
    ["worker_role"]
)

ACTIVE_SHARED_WORKERS = Gauge(
    "active_shared_workers",
    "Currently active shared workers",
)

ACTIVE_VIP_WORKERS = Gauge(
    "active_vip_workers",
    "Currently active vip workers",
)

WORKER_ACTIVE_STATE = Gauge(
    "workers_active_state",
    "Currently active worker state",
    ["worker_role", "worker_id"]
)

SCALING_EVENTS_TOTAL = Counter(
    "scaling_events_total",
    "Total number of scaling events",
    ["tier", "direction"]
)

#---------------------------------
# Reliability
#---------------------------------

DEAD_LETTER_QUEUE_JOBS_TOTAL =  Counter(
    "dlq_jobs_total",
    "Total number of dead letter queue jobs",
    ["reason"]
)

DEAD_LETTER_QUEUE_PUSH_ATTEMPTS_TOTAL =  Counter(
    "dlq_push_attempt_total",
    "Total number of dead letter queue push attempts",
    ["reason"]
)

DLQ_PUSH_FAILURE_TOTAL = Counter(
    "dlq_push_failure_total",
    "Total number of failed DLQ push attempts",
    ["reason"]
)

REDIS_OPERATION_FAILURES_TOTAL = Counter(
    "redis_operation_failures_total",
    "Total Redis operation failures",
    ["operation"]
)


# model
MODEL_LOAD_TIME = Histogram(
    "model_load_time_seconds",
    "Time spent loading model artifact",
    ["model_name", "model_version", "model_runtime"]
)


MODEL_INFERENCE_LATENCY = Histogram(
    "model_inference_latency_seconds",
    "Model Inference latency",
    ["model_name", "model_version", "model_runtime", "tier"],
)

MODEL_INFERENCE_REQUESTS = Counter(
    "model_inference_requests_total",
    "Total model inference requests",
    ["model_name", "model_version", "model_runtime", "tier", "result"],
)

MODEL_BATCH_SIZE = Histogram(
    "model_batch_size",
    "Number of requests processed per inference batch",
    ["model_name", "model_version", "model_runtime", "tier"],
)