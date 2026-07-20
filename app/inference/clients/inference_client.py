import logging
import numpy as np
import time
import tritonclient.http as httpclient

from app.inference.features import extract_features, Features
from app.inference.config import PredictionResult
from app.inference.model_selection import determine_model_name, determine_model_versions_based_on_rollout_mode, \
    SelectedModelVersions
from app.shared.metrics import WORKER_TRITON_REQUEST_LATENCY_SECONDS, WORKER_TRITON_SERIALIZATION_SECONDS, \
    WORKER_TRITON_DESERIALIZATION_SECONDS, PREDICTION_RESULT_TOTAL, PREDICTION_SCORE_HISTOGRAM, \
    PREDICTION_AGREEMENT_TOTAL, PREDICTION_DISAGREEMENT_TOTAL, PREDICTION_SCORE_DIFF, WORKER_PROCESSING_FAILURES_TOTAL
from tritonclient.http import InferResult, InferRequestedOutput, InferInput

logger = logging.getLogger(__name__)

TRITON_CLIENT = httpclient.InferenceServerClient(url="triton:8000")

def process_anomaly_detection(transactions:list[dict]) -> list[PredictionResult]:
    results: list[PredictionResult] = []

    for transaction in transactions:
        try:
            features: Features = extract_features(transaction)
            result: PredictionResult = process_transaction(features)
            results.append(result)

        except Exception as e:
            tier = transaction.get("tier", "unknown")

            record_worker_failure(
                stage="transaction_processing",
                error=e,
                tier=tier,
            )

            logger.exception(
                "Failed to process transaction",
                extra={"tier": tier},
            )

            continue

    return results

def process_transaction(features: Features) -> PredictionResult:
    try:
        model_name: str = determine_model_name()
        versions: SelectedModelVersions = determine_model_versions_based_on_rollout_mode(model_name)

    except Exception as e:
        record_worker_failure(
            stage="model_selection",
            error=e,
            tier=features.tier,
        )
        logger.exception("Failed to determine model selection")
        raise

    stable = infer_single_version(features, versions.primary_version, model_name)

    if versions.shadow_version is not None:
        try:
            shadow = infer_single_version(features, versions.shadow_version, model_name)
            record_shadow_comparison(stable, shadow, model_name)

        except Exception as e:
            record_worker_failure(
                stage="shadow_inference",
                error=e,
                tier=features.tier,
                model_name=model_name,
                model_version=versions.shadow_version,
            )

            logger.exception(
                "Shadow inference failed; returning stable prediction",
                extra={
                    "model_name": model_name,
                    "shadow_version": versions.shadow_version,
                    "tier": _label_value(features.tier),
                },
            )

    return stable

def infer_single_version(features: Features, model_version: str, model_name: str) -> PredictionResult:
    triton_inputs: list[InferInput] = preprocess_input(features, model_version, model_name)
    raw_response: InferResult = run_inference(triton_inputs, features, model_version, model_name)
    return postprocess_output(raw_response, features, model_version, model_name)

def preprocess_input(features: Features, model_version: str, model_name: str) -> list[InferInput]:
    serialize_start = time.perf_counter()

    try:
        raw_data = np.array([[features.amount]], dtype=np.float32)
        shape = list(raw_data.shape)

        inputs: list[InferInput] = [
            httpclient.InferInput(
                name="INPUT",
                shape=shape,
                datatype="FP32",
            )
        ]

        inputs[0].set_data_from_numpy(raw_data)

        return inputs

    except Exception as e:
        record_worker_failure(
            stage="triton_serialization",
            error=e,
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        )
        logger.exception("Failed to serialize Triton input")
        raise

    finally:
        serialize_end = time.perf_counter()

        WORKER_TRITON_SERIALIZATION_SECONDS.labels(
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        ).observe(serialize_end - serialize_start)

def run_inference(inputs: list[InferInput], features: Features, model_version: str, model_name: str) -> InferResult:
    outputs: list[InferRequestedOutput] = [
        httpclient.InferRequestedOutput("OUTPUT"),
        httpclient.InferRequestedOutput("SCORE")
    ]

    network_start = time.perf_counter()

    try:
        response = TRITON_CLIENT.infer(
            model_name=model_name,
            model_version=model_version,
            inputs=inputs,
            outputs=outputs,
        )

        return response

    except Exception as e:
        record_worker_failure(
            stage="triton_request",
            error=e,
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        )
        logger.exception("Triton inference request failed")
        raise

    finally:
        network_end = time.perf_counter()

        WORKER_TRITON_REQUEST_LATENCY_SECONDS.labels(
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        ).observe(network_end - network_start)

def postprocess_output(raw_response: InferResult, features: Features, model_version: str, model_name: str) -> PredictionResult:
    deserialize_start = time.perf_counter()

    try:
        is_anomaly_raw = raw_response.as_numpy("OUTPUT")
        score_raw = raw_response.as_numpy("SCORE")

        is_anomaly_value = int(is_anomaly_raw.reshape(-1)[0])
        score_value = float(score_raw.reshape(-1)[0])

        result = PredictionResult(
            is_anomaly=bool(is_anomaly_value == 1),
            score=score_value,
            tier=features.tier,
            model_version=model_version,
        )

        PREDICTION_RESULT_TOTAL.labels(
            model_name=model_name,
            model_version=model_version,
            result="anomaly" if result.is_anomaly else "normal",
        ).inc()

        PREDICTION_SCORE_HISTOGRAM.labels(
            model_name=model_name,
            model_version=model_version,
        ).observe(score_value)

        return result

    except Exception as e:
        record_worker_failure(
            stage="triton_deserialization",
            error=e,
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        )
        logger.exception("Failed to deserialize Triton response")
        raise

    finally:
        deserialize_end = time.perf_counter()

        WORKER_TRITON_DESERIALIZATION_SECONDS.labels(
            tier=features.tier,
            model_name=model_name,
            model_version=model_version,
        ).observe(deserialize_end - deserialize_start)

def record_shadow_comparison(
        stable_version: PredictionResult,
        shadow_version: PredictionResult,
        model_name: str,
) -> None:
    try:
        if stable_version.is_anomaly == shadow_version.is_anomaly:
            PREDICTION_AGREEMENT_TOTAL.labels(model_name=model_name).inc()
        else:
            PREDICTION_DISAGREEMENT_TOTAL.labels(model_name=model_name).inc()

        PREDICTION_SCORE_DIFF.labels(
            model_name=model_name,
        ).observe(abs(shadow_version.score - stable_version.score))

    except Exception as e:
        record_worker_failure(
            stage="shadow_comparison",
            error=e,
            tier=stable_version.tier,
            model_name=model_name,
            model_version=shadow_version.model_version,
        )
        logger.exception("Failed to record shadow comparison")
        raise

def get_model_metadata():
    try:
        model_name = determine_model_name()
        metadata: dict = TRITON_CLIENT.get_model_metadata(model_name)

        return {
            "name": metadata.get("name", "unknown"),
            "version": (metadata.get("versions") or ["unknown"])[0],
        }

    except Exception as e:
        record_worker_failure(
            stage="model_metadata_fetch",
            error=e,
        )

        logger.exception("Failed to get model metadata")

        return {
            "name": "unknown",
            "version": "unknown",
        }


def _label_value(value) -> str:
    if value is None:
        return "unknown"

    return str(getattr(value, "value", value))


def record_worker_failure(
        stage: str,
        error: Exception,
        tier: str | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
) -> None:
    WORKER_PROCESSING_FAILURES_TOTAL.labels(
        stage=stage,
        error_type=type(error).__name__,
        tier=_label_value(tier),
        model_name=model_name or "unknown",
        model_version=model_version or "unknown",
    ).inc()