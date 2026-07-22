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

LOAD_SHED_REQUESTS_TOTAL = Counter(
    "load_shed_requests_total",
    "Total number of requests intentionally rejected by load shedding",
    ["tier", "reason"]
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

WORKER_BATCH_SIZE = Histogram(
    "worker_batch_size",
    "Observed number of jobs included in each worker batch",
    ["worker_role", "tier", "flush_reason"],
    buckets=(1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048),
)

WORKER_BATCH_FLUSH_TOTAL = Counter(
    "worker_batch_flush_total",
    "Total number of worker batch flushes",
    ["worker_role", "tier", "reason"]
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


# Triton Inference Server Client

WORKER_PROCESSING_LATENCY = Histogram(
    "worker_processing_latency_seconds",
    "Time spent processing inference jobs",
    ["worker_role", "tier"]

)

WORKER_PROCESSING_FAILURES_TOTAL = Counter(
    "worker_processing_failures_total",
    "Total number of worker processing failures by stage",
    ["stage", "error_type", "tier", "model_name", "model_version"],
)

WORKER_TRITON_REQUEST_LATENCY_SECONDS = Histogram(
    "worker_triton_request_latency_seconds",
    "Time spent on Triton Inference anomaly detection",
    ["model_name", "model_version","tier"]
)

WORKER_TRITON_SERIALIZATION_SECONDS = Histogram(
    "worker_triton_serialization_seconds",
    "Time spent on Triton request serialization",
    ["model_name", "model_version","tier"]
)

WORKER_TRITON_DESERIALIZATION_SECONDS = Histogram(
    "worker_triton_deserialization_seconds",
    "Time spent on Triton response deserialization",
    ["model_name", "model_version","tier"]
)

# model behaviour

PREDICTION_AGREEMENT_TOTAL = Counter(
    "prediction_agreement_total",
    "model version 1 and model version 2 prediction have the same result",
    ["model_name"]
)

PREDICTION_DISAGREEMENT_TOTAL = Counter(
    "prediction_disagreement_total",
    "model version 1 and model version 2 prediction have different result",
    ["model_name"]
)

PREDICTION_RESULT_TOTAL = Counter(
    "prediction_result_total",
    "Prediction count by model version and result",
    ["model_name", "model_version", "result"]
)

PREDICTION_SCORE_HISTOGRAM = Histogram(
    "prediction_score",
    "Anomaly score distribution by model version",
    ["model_name", "model_version"],
    buckets=[-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0]
)

PREDICTION_SCORE_DIFF = Histogram(
    "prediction_score_diff",
    "absolute anomaly score difference between model versions",
    ["model_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)
