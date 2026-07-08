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
    WORKER_TRITON_DESERIALIZATION_SECONDS, PREDICTION_RESULT_TOTAL, PREDICTION_SCORE_HISTOGRAM, \
    PREDICTION_AGREEMENT_TOTAL, PREDICTION_DISAGREEMENT_TOTAL, PREDICTION_SCORE_DIFF
from app.shared.redis import redis_client
from tritonclient.http import InferResult, InferRequestedOutput, InferInput

logger = logging.getLogger(__name__)

TRITON_MODEL_NAME = os.getenv("TRITON_MODEL_NAME", "unknown")
TRITON_CLIENT = httpclient.InferenceServerClient(url="triton:8000")

def process_anomaly_detection(transactions:list[dict]) -> list[PredictionResult]:
    results = []
    try:
        for transaction in transactions:
            features: Features = extract_features(transaction)
            result = process_transaction(features)
            results.append(result)

    except Exception as e:
        logger.error(f" Inference Exception: {e}")

    return results

def process_transaction(features):
    mode = os.getenv("MODEL_ROLLOUT_MODE", "stable")
    stable_version = os.getenv("STABLE_MODEL_VERSION", "1")
    candidate_version = os.getenv("CANDIDATE_MODEL_VERSION", "2")

    if mode == "stable":
        return infer_single_version(features, stable_version)

    if mode == "canary":
        version = choose_model_version(
            stable_version = stable_version,
            candidate_version=candidate_version
        )
        return infer_single_version(features, version)

    if mode == "shadow":
        stable = infer_single_version(features, stable_version)
        candidate = infer_single_version(features, candidate_version)
        record_shadow_comparison(stable, candidate)
        return stable

    raise ValueError(f"Unknown rollout mode: {mode}")

def choose_model_version(stable_version: str, candidate_version: str) -> str:
    canary_percentage = float(os.getenv("MODEL_VERSION_2_CANARY_PERCENTAGE", "0.0"))
    if random.random() < canary_percentage:
        return candidate_version
    return stable_version

def infer_single_version(features: Features, model_version) -> PredictionResult:
    triton_inputs: list[InferInput] = preprocess_input(features, model_version)
    raw_response: InferResult = run_inference(model_version, triton_inputs, features)
    return postprocess_output(raw_response, features, model_version)

def preprocess_input(features: Features, model_version) -> list[InferInput]:
    # prepare numpy arrays
    raw_data = np.array([[features.amount]], dtype=np.float32) # Shape: (1,)
    shap = list(raw_data.shape) # Explicitly cast tuple to list

    inputs: list[InferInput] = [
        httpclient.InferInput(
            name="INPUT",
            shape=shap,
            datatype="FP32"
        )
    ]

    serialize_start = time.perf_counter()

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
    outputs: list[InferRequestedOutput] = [
        httpclient.InferRequestedOutput("OUTPUT"),
        httpclient.InferRequestedOutput("SCORE")
    ]

    network_start = time.perf_counter()

    response = TRITON_CLIENT.infer(
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

    PREDICTION_RESULT_TOTAL.labels(
        model_name = TRITON_MODEL_NAME,
        model_version = model_version,
        result = "anomaly" if bool(is_anomaly[0] == 1) else "normal"
    ).inc()

    PREDICTION_SCORE_HISTOGRAM.labels(
        model_name = TRITON_MODEL_NAME,
        model_version = model_version,
    ).observe(float(score[0]))

    return result

def record_shadow_comparison(v1: PredictionResult, v2: PredictionResult) -> None:
    if v1.is_anomaly == v2.is_anomaly:
        PREDICTION_AGREEMENT_TOTAL.labels(model_name=TRITON_MODEL_NAME).inc()
    else:
        PREDICTION_DISAGREEMENT_TOTAL.labels(model_name=TRITON_MODEL_NAME).inc()

    PREDICTION_SCORE_DIFF.labels(
        model_name=TRITON_MODEL_NAME
    ).observe(abs(v2.score - v1.score))

def get_model_metadata():
    try:
        metadata: dict = TRITON_CLIENT.get_model_metadata(TRITON_MODEL_NAME)
        model_metadata = {
            "name": metadata.get("name", "unknown"),
            "version": (metadata.get('versions') or ['unknown'])[0]
        }
        return model_metadata

    except Exception as e:
        logger.error(f"Failed to get model metadata, exception: {e}")