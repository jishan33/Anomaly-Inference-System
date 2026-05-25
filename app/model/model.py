from typing import NamedTuple
from sklearn.ensemble import IsolationForest
from pydantic import BaseModel, Field

from app.model.features import Features

class PredictionResult(NamedTuple):
    is_anomaly: bool
    score: float
    tier: str

class Model:
    def __init__(self):
        self.model = None

    def load(self):
        """Load or initialize model"""
        self.model = IsolationForest(
            contamination=0.1,
            random_state=42
        )

        # Fake training data (for now)
        data = [[10], [20], [30],[40], [50]]
        self.model.fit(data)

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