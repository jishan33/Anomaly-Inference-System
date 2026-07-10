from pathlib import Path
from typing import Any

import yaml


class ModelRegistry:
    def __init__(self, registry_path: str = "app/model_registry/models.yaml"):
        self.registry_path = Path(registry_path)
        self.registry = self._load_registry()

    def _load_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            raise FileNotFoundError(f"Model registry not found: {self.registry_path}")

        with self.registry_path.open("r") as file:
            return yaml.safe_load(file)

    def get_model(self, model_name: str) -> dict[str, Any]:
        models =self.registry.get("models", {})

        if model_name not in models:
            raise ValueError(f"Model not found in registry: {model_name}")

        return models[model_name]

    def resolve_version(self, model_name: str, alias_or_version: str) -> str:
        model = self.get_model(model_name)

        aliases = model.get("aliases", {})
        versions = model.get("versions", {})

        if alias_or_version in aliases:
            return aliases[alias_or_version]

        if alias_or_version in versions:
            return alias_or_version

        raise ValueError( f"Could not resolve version '{alias_or_version}' for model '{model_name}' ")

    def get_version_metadata(self, model_name: str, alias_or_version: str) -> dict[str, Any]:
        model = self.get_model(model_name)
        resolved_version = self.resolve_version(model_name, alias_or_version)

        return model["versions"][resolved_version]

    def is_rollout_eligible(self, model_name: str, alias_over_version: str) -> bool:
        metadata = self.get_version_metadata(model_name, alias_over_version)

        return bool(metadata.get("rollout_eligible", False))