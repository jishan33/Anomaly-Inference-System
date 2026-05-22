from app.model.autoscaler import Autoscaler


autoscaler = Autoscaler()
print("run_autoscaler.py started")
autoscaler.autoscaler_loop()