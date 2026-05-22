
from .model import model_instance, PredictionResult
from .features import extract_features
import time
from app.model.metrics import MODEL_LATENCY, MODEL_PREDICTIONS


def run_inference(transactions:list[dict]) -> list[PredictionResult]:
    results = []
    for transaction in transactions:
        request_start = time.time()

        features = extract_features(transaction)
        result = model_instance.predict(features)

        MODEL_LATENCY.observe(time.time()-request_start)
        MODEL_PREDICTIONS.labels(result="anomaly" if result.is_anomaly else "normal").inc()
        results.append(result)

    return results
