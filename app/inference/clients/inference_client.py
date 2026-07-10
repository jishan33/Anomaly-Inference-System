import logging
import os
import numpy as np
import time
import tritonclient.http as httpclient

from app.inference.features import extract_features, Features
from app.inference.config import PredictionResult
from app.inference.model_selection import determine_model_name, determine_model_versions_based_on_rollout_mode
from app.shared.metrics import WORKER_TRITON_REQUEST_LATENCY_SECONDS, WORKER_TRITON_SERIALIZATION_SECONDS, \
    WORKER_TRITON_DESERIALIZATION_SECONDS, PREDICTION_RESULT_TOTAL, PREDICTION_SCORE_HISTOGRAM, \
    PREDICTION_AGREEMENT_TOTAL, PREDICTION_DISAGREEMENT_TOTAL, PREDICTION_SCORE_DIFF
from tritonclient.http import InferResult, InferRequestedOutput, InferInput

logger = logging.getLogger(__name__)

TRITON_CLIENT = httpclient.InferenceServerClient(url="triton:8000")

def process_anomaly_detection(transactions:list[dict]) -> list[PredictionResult]:
    results = []
    try:
        for transaction in transactions:
            features: Features = extract_features(transaction)
            model_name: str = determine_model_name()
            result: PredictionResult = process_transaction(features, model_name)
            results.append(result)

    except Exception as e:
        logger.error(f" Inference Exception: {e}")

    return results

def process_transaction(features: Features, model_name: str) -> PredictionResult:
    versions = determine_model_versions_based_on_rollout_mode(model_name)
    logger.info(f"Versions: {versions}")

    stable = infer_single_version(features, versions.primary_version, model_name)

    if versions.shadow_version is not None:
        shadow = infer_single_version(features, versions.shadow_version, model_name)
        record_shadow_comparison(stable, shadow, model_name)

    return stable

def infer_single_version(features: Features, model_version: str, model_name: str) -> PredictionResult:
    triton_inputs: list[InferInput] = preprocess_input(features, model_version, model_name)
    raw_response: InferResult = run_inference(triton_inputs, features, model_version, model_name)
    return postprocess_output(raw_response, features, model_version, model_name)

def preprocess_input(features: Features, model_version: str, model_name: str) -> list[InferInput]:
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
        model_name = model_name,
        model_version = model_version
    ).observe(serialize_end - serialize_start)

    return inputs

def run_inference(inputs: list[InferInput], features: Features, model_version: str, model_name: str) -> InferResult:
    outputs: list[InferRequestedOutput] = [
        httpclient.InferRequestedOutput("OUTPUT"),
        httpclient.InferRequestedOutput("SCORE")
    ]

    network_start = time.perf_counter()

    response = TRITON_CLIENT.infer(
        model_name=model_name,
        model_version=model_version,
        inputs= inputs,
        outputs= outputs
    )

    network_end = time.perf_counter()
    WORKER_TRITON_REQUEST_LATENCY_SECONDS.labels(
        tier= features.tier,
        model_name = model_name,
        model_version = model_version
    ).observe(network_end - network_start)

    return response

def postprocess_output(raw_response: InferResult, features: Features, model_version: str, model_name: str) -> PredictionResult:
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
        model_name = model_name,
        model_version = model_version
    ).observe(deserialize_end - deserialize_start)

    PREDICTION_RESULT_TOTAL.labels(
        model_name = model_name,
        model_version = model_version,
        result = "anomaly" if bool(is_anomaly[0] == 1) else "normal"
    ).inc()

    PREDICTION_SCORE_HISTOGRAM.labels(
        model_name = model_name,
        model_version = model_version,
    ).observe(float(score[0]))

    return result

def record_shadow_comparison(stable_version: PredictionResult, shadow_version: PredictionResult, model_name: str) -> None:
    if stable_version.is_anomaly == shadow_version.is_anomaly:
        PREDICTION_AGREEMENT_TOTAL.labels(model_name=model_name).inc()
    else:
        PREDICTION_DISAGREEMENT_TOTAL.labels(model_name=model_name).inc()

    PREDICTION_SCORE_DIFF.labels(
        model_name=model_name
    ).observe(abs(shadow_version.score - stable_version.score))

def get_model_metadata(request_type: str):
    try:
        model_name = determine_model_name(request_type)
        metadata: dict = TRITON_CLIENT.get_model_metadata(model_name)
        model_metadata = {
            "name": metadata.get("name", "unknown"),
            "version": (metadata.get('versions') or ['unknown'])[0]
        }
        return model_metadata

    except Exception as e:
        logger.error(f"Failed to get model metadata, exception: {e}")