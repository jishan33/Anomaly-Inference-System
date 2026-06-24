import logging

import numpy as np
import tritonclient.http as httpclient
from .features import extract_features
from .model import PredictionResult

logger = logging.getLogger(__name__)

def run_inference(transactions:list[dict]) -> list[PredictionResult]:
    # POST http://localhost:8001/v2/models/anomaly_detector/infer
    triton_client = httpclient.InferenceServerClient(url="host.docker.internal:8001")
    logger.info(f"triton_client: {triton_client}")
    input_data = np.array([5000], dtype=np.float32)
    inputs = [
        httpclient.InferInput(name="INPUT", shape=input_data.shape, datatype="FP32")
    ]

    outputs = [
        httpclient.InferRequestedOutput("OUTPUT")
    ]
    results = []
    try:
        for transaction in transactions:
            features = extract_features(transaction)

            raw_data = np.array([features.amount], dtype=np.float32)
            inputs[0].set_data_from_numpy(raw_data)
            logger.info(f"inputs[0]: {inputs[0]}")

            response = triton_client.infer(
                model_name="anomaly_detector",
                inputs= inputs,
                outputs= outputs
            )
            is_anomaly = response.as_numpy("OUTPUT")
            logger.info(f"is_anomaly: {is_anomaly}")

            result = PredictionResult(
                is_anomaly= bool(is_anomaly[0] == 1),
                score=0,
                tier=features.tier

            )
            results.append(result)

    except Exception as e:
        logger.error(f" Inference Exception: {e}")

    return results
