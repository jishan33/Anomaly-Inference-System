from prometheus_client import Histogram, Counter

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