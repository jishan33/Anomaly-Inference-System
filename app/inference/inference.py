import json
import logging
import time

import numpy as np
import tritonclient.http as httpclient
from .features import extract_features
from .model import PredictionResult
from ..shared.metrics import WORKER_TRITON_REQUEST_LATENCY_SECONDS, WORKER_TRITON_SERIALIZATION_SECONDS, \
    WORKER_TRITON_DESERIALIZATION_SECONDS
from ..shared.redis import redis_client

logger = logging.getLogger(__name__)


def run_inference(transactions:list[dict]) -> list[PredictionResult]:
    triton_client = httpclient.InferenceServerClient(url="triton:8000")
    input_data = np.array([5000], dtype=np.float32)
    inputs = [
        httpclient.InferInput(name="INPUT", shape=input_data.shape, datatype="FP32")
    ]
    outputs = [
        httpclient.InferRequestedOutput("OUTPUT")
    ]

    raw_json = redis_client.get("model_metadata")
    model_metadata = json.loads(raw_json)

    results = []
    try:
        for transaction in transactions:
            # prepare numpy arrays
            serialize_start = time.perf_counter()
            features = extract_features(transaction)
            raw_data = np.array([features.amount], dtype=np.float32)
            inputs[0].set_data_from_numpy(raw_data)
            logger.info(f"inputs[0]: {inputs[0]}")
            serialize_end = time.perf_counter()

            WORKER_TRITON_SERIALIZATION_SECONDS.labels(
                tier= features.tier,
                model_name = model_metadata['name'],
                model_version = model_metadata['version']
            ).observe(serialize_end - serialize_start)


            # network start
            network_start = time.perf_counter()
            response = triton_client.infer(
                model_name="anomaly_detector",
                inputs= inputs,
                outputs= outputs
            )
            network_end = time.perf_counter()

            WORKER_TRITON_REQUEST_LATENCY_SECONDS.labels(
              tier= features.tier,
              model_name = model_metadata['name'],
              model_version = model_metadata['version']
            ).observe(network_end - network_start)

            # convert output
            deserialize_start = time.perf_counter()
            is_anomaly = response.as_numpy("OUTPUT")
            logger.info(f"is_anomaly: {is_anomaly}")

            result = PredictionResult(
                is_anomaly= bool(is_anomaly[0] == 1),
                score=0,
                tier=features.tier

            )
            deserialize_end = time.perf_counter()

            WORKER_TRITON_DESERIALIZATION_SECONDS.labels(
                tier= features.tier,
                model_name = model_metadata['name'],
                model_version = model_metadata['version']
            ).observe(deserialize_end - deserialize_start)

            results.append(result)

    except Exception as e:
        logger.error(f" Inference Exception: {e}")

    return results
