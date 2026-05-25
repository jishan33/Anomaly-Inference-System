from app.model.model import model_instance
from app.model.inference import run_inference

model_instance.load()

result = run_inference({"amount": 1000})
print(result)