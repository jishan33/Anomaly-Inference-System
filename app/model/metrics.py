from prometheus_client import Counter, Histogram, Gauge

# Model
MODEL_LATENCY = Histogram(
    "fastapi_model_latency_seconds",
    "Model latency in seconds"
)

MODEL_PREDICTIONS = Counter(
    "model_predictions_total",
    "Total number of model predictions",
    ["result"]
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

