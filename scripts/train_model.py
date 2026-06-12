import pickle
from pathlib import Path
from sklearn.ensemble import IsolationForest

MODEL_DIR = Path("models/anomaly-detector/v1")
MODEL_PATH = MODEL_DIR / "model.pkl"

model = IsolationForest(
    contamination=0.1,
    random_state=42,
)

# Fake training data for now
data = [[10], [20], [30], [40], [50]]
model.fit(data)

if MODEL_PATH.exists():
    print(
        f"Abort! A model already exists at {MODEL_PATH}. "
        "Clean it up or change the version name."
    )
else:
    with open(MODEL_DIR / "model.pkl", "wb") as f:
        pickle.dump(model, f)

    print("Model saved successfully")