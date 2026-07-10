import os
import random
from typing import NamedTuple
from app.model_registry.model_registry import ModelRegistry

model_registry = ModelRegistry()

class SelectedModelVersions(NamedTuple):
    primary_version: str
    shadow_version: str | None = None


def determine_model_name() -> str:
    request_type = os.getenv("ANOMALY_MODEL", "unknown")

    if request_type == "transaction_anomaly":
        return "transaction_anomaly_detector"

    if request_type == "volume_anomaly":
        return "volume_anomaly_detector"

    raise ValueError(f"Unsupported request type: {request_type}")

def resolve_rollout_eligible_version(model_name: str, alias_or_version: str) -> str:
    version = model_registry.resolve_version(
        model_name= model_name,
        alias_or_version= alias_or_version
    )

    if not model_registry.is_rollout_eligible(model_name, version):
        raise RuntimeError(
            f"Model {model_name}:{version} is not rollout eligible"
        )

    return version

def determine_model_versions_based_on_rollout_mode(model_name: str) -> SelectedModelVersions:
    mode = os.getenv("MODEL_ROLLOUT_MODE", "stable")

    stable_version = resolve_rollout_eligible_version(
        model_name= model_name,
        alias_or_version= "stable"
    )

    if mode == "stable":
        return SelectedModelVersions(primary_version= stable_version)

    elif mode == "canary":
        candidate_version = resolve_rollout_eligible_version(
            model_name= model_name,
            alias_or_version= mode
        )

        selected_version = choose_model_version_for_canary_rollout_mode(
            primary_version= stable_version,
            candidate_version= candidate_version
        )
        return SelectedModelVersions(primary_version= selected_version)

    elif mode == "shadow":
        shadow_version = resolve_rollout_eligible_version(
            model_name= model_name,
            alias_or_version= mode
        )
        return SelectedModelVersions(primary_version= stable_version, shadow_version= shadow_version)

    else: raise ValueError(f"Unknown rollout mode: {mode}")

def choose_model_version_for_canary_rollout_mode(primary_version: str, candidate_version: str) -> str:
    canary_fraction = float(os.getenv("MODEL_CANARY_FRACTION", "0.0"))

    if random.random() < canary_fraction:
        return candidate_version

    return primary_version

