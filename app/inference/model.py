import json
import logging
import pickle
import time
from pathlib import Path
from typing import NamedTuple
from pydantic import BaseModel, Field

from app.inference.features import Features
from app.shared.metrics import MODEL_LOAD_TIME

logger = logging.getLogger(__name__)
MODEL_DIR = Path("models/anomaly-detector/v1")

class PredictionResult(NamedTuple):
    is_anomaly: bool
    score: float
    tier: str

class Model:
    def __init__(self):
        self.model = None
        self.metadata = None

    def load(self):
        start = time.time()

        self.metadata = self.load_model_metadata()

        model_path = MODEL_DIR/"model.pkl"
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

        duration = time.time() - start
        MODEL_LOAD_TIME.labels(
            model_name = self.metadata["model_name"],
            model_version = self.metadata["model_version"],
            model_runtime = self.metadata["model_runtime"]
        ).observe(duration)

        logger.info(f"model metadata: {self.metadata}")

    def predict(self, features: Features) -> PredictionResult:
        feature_vector = [[features.amount]]
        prediction = self.model.predict(feature_vector)[0]
        score = self.model.decision_function(feature_vector)[0]

        return PredictionResult(
            is_anomaly= bool(prediction==-1),
            score=float(score),
            tier=features.tier
        )

    @staticmethod
    def load_model_metadata():
        file_path = MODEL_DIR/"metadata.json"
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
                return data
        except Exception as e:
            logger.error(f"Error loading {file_path}, details: {e}")
            return None

class PredictRequest(BaseModel):
    customer_token:str
    amount: float = Field(...,gt=0)
    tier: str

class PredictResponse(BaseModel):
    is_anomaly:bool
    score: float


# Single model instance (IMPORTANT for infra pattern)
model_instance = Model()