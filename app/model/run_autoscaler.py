import logging

from app.model.autoscaler import Autoscaler
logging.getLogger("auto_scaler")

autoscaler = Autoscaler()
logging.info("run_autoscaler.py started")
autoscaler.autoscaler_loop()