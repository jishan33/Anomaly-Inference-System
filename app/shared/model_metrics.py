from prometheus_client import Histogram

MODEL_LOAD_TIME = Histogram(
    "model_load_time_seconds",
    "Time spent loading model artifact",
    ["model_name", "model_version", "model_runtime"]
)