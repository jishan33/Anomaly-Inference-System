import json
import logging
import os
import random

import numpy as np
import time
import tritonclient.http as httpclient

from app.inference.features import extract_features, Features
from app.inference.model import PredictionResult
from app.shared.metrics import WORKER_TRITON_REQUEST_LATENCY_SECONDS, WORKER_TRITON_SERIALIZATION_SECONDS, \
    WORKER_TRITON_DESERIALIZATION_SECONDS
from app.shared.redis import redis_client
from tritonclient.http import InferResult, InferRequestedOutput, InferInput

logger = logging.getLogger(__name__)
MODEL_VERSION_2_CANARY_PERCENTAGE = float(os.getenv("MODEL_VERSION_2_CANARY_PERCENTAGE", "0.0"))
TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "unknown")

def choose_model_version() -> str:
    if random.random() < MODEL_VERSION_2_CANARY_PERCENTAGE:
        return "2"
    return  "1"

def process_anomaly_detection(transactions:list[dict]) -> list[PredictionResult]:
    results = []
    try:
        for transaction in transactions:
            features: Features = extract_features(transaction)

            model_version = choose_model_version()

            triton_inputs: list[InferInput] = preprocess_input(features, model_version)

            raw_response: InferResult = run_inference(model_version, triton_inputs, features)

            application_output = postprocess_output(raw_response, features, model_version)

            results.append(application_output)

    except Exception as e:
        logger.error(f" Inference Exception: {e}")

    return results

def get_model_metadata():
    try:
        triton_client = httpclient.InferenceServerClient(url="triton:8000")
        metadata: dict = triton_client.get_model_metadata(TRITON_MODEL_NAME)
        model_metadata = {
            "name": metadata.get("name", "unknown"),
            "version": (metadata.get('versions') or ['unknown'])[0]
        }
        return model_metadata

    except Exception as e:
       logger.error(f"Failed to get model metadata, exception: {e}")

def preprocess_input(features: Features, model_version) -> list[InferInput]:
    # prepare numpy arrays
    input_data = np.array([[5000]], dtype=np.float32)
    inputs: list[InferInput] = [
        httpclient.InferInput(
            name="INPUT",
            shape=list(input_data.shape), # Explicitly cast tuple to list
            datatype="FP32"
        )
    ]

    serialize_start = time.perf_counter()

    raw_data = np.array([[features.amount]], dtype=np.float32) # Shape: (1,)
    inputs[0].set_data_from_numpy(raw_data)
    logger.info(f"inputs[0]: {inputs[0]}")

    serialize_end = time.perf_counter()
    WORKER_TRITON_SERIALIZATION_SECONDS.labels(
        tier= features.tier,
        model_name = TRITON_MODEL_NAME,
        model_version = model_version
    ).observe(serialize_end - serialize_start)

    return inputs

def run_inference(model_version: str, inputs: list[InferInput], features: Features) -> InferResult:
    triton_client = httpclient.InferenceServerClient(url="triton:8000")

    outputs: list[InferRequestedOutput] = [
        httpclient.InferRequestedOutput("OUTPUT"),
        httpclient.InferRequestedOutput("SCORE")
    ]

    network_start = time.perf_counter()

    response = triton_client.infer(
        model_name=TRITON_MODEL_NAME,
        model_version=model_version,
        inputs= inputs,
        outputs= outputs
    )

    network_end = time.perf_counter()
    WORKER_TRITON_REQUEST_LATENCY_SECONDS.labels(
        tier= features.tier,
        model_name = TRITON_MODEL_NAME,
        model_version = model_version
    ).observe(network_end - network_start)

    return response

def postprocess_output(raw_response: InferResult, features: Features, model_version) -> PredictionResult:
    deserialize_start = time.perf_counter()

    is_anomaly = raw_response.as_numpy("OUTPUT")
    logger.info(f"is_anomaly: {is_anomaly}")

    score = raw_response.as_numpy("SCORE")
    logger.info(f"score: {score}")

    result = PredictionResult(
        is_anomaly= bool(is_anomaly[0] == 1),
        score= float(score[0]),
        tier= features.tier,
        model_version= model_version
    )

    deserialize_end = time.perf_counter()
    WORKER_TRITON_DESERIALIZATION_SECONDS.labels(
        tier= features.tier,
        model_name = TRITON_MODEL_NAME,
        model_version = model_version
    ).observe(deserialize_end - deserialize_start)

    return result