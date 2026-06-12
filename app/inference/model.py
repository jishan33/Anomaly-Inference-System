import json
import logging
import pickle
from pathlib import Path
from typing import NamedTuple
from sklearn.ensemble import IsolationForest
from pydantic import BaseModel, Field

from app.inference.features import Features

logger = logging.getLogger(__name__)

class PredictionResult(NamedTuple):
    is_anomaly: bool
    score: float
    tier: str

class Model:
    def __init__(self):
        self.model = None

    def load(self):
        model_path = Path("models/anomaly-detector/v1/model.pkl")
        with open(model_path, "rb") as f:
            self.model = pickle.load(f)

    def predict(self, features: Features) -> PredictionResult:
        """Return anomaly score + label"""
        feature_vector = [[features.amount]]
        prediction = self.model.predict(feature_vector)[0]
        score = self.model.decision_function(feature_vector)[0]

        return PredictionResult(
            is_anomaly= bool(prediction==-1),
            score=float(score),
            tier=features.tier
        )

class PredictRequest(BaseModel):
    customer_token:str
    amount: float = Field(...,gt=0)
    tier: str

class PredictResponse(BaseModel):
    is_anomaly:bool
    score: float


# Single model instance (IMPORTANT for infra pattern)
model_instance = Model()