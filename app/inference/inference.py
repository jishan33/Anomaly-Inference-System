
import time
from importlib.metadata import metadata

from .features import extract_features
from .model import model_instance, PredictionResult
from app.shared.metrics import MODEL_INFERENCE_LATENCY, MODEL_INFERENCE_REQUESTS


def run_inference(transactions:list[dict]) -> list[PredictionResult]:
    results = []
    for transaction in transactions:
        request_start = time.time()

        features = extract_features(transaction)
        result = model_instance.predict(features)

        duration = time.time() - request_start
        MODEL_INFERENCE_LATENCY.labels(
            model_name = model_instance.metadata["model_name"],
            model_version = model_instance.metadata["model_version"],
            model_runtime = model_instance.metadata["model_runtime"],
            tier = result.tier
        ).observe(duration)

        MODEL_INFERENCE_REQUESTS.labels(
            model_name = model_instance.metadata["model_name"],
            model_version = model_instance.metadata["model_version"],
            model_runtime = model_instance.metadata["model_runtime"],
            result="anomaly" if result.is_anomaly else "normal",
            tier = result.tier
        ).inc()

        results.append(result)

    return results
