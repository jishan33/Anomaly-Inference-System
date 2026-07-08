import joblib
import numpy
import numpy as np
import sklearn
import triton_python_backend_utils as pb_utils

class TritonPythonModel:
    def initialize(self, args):
        self.model = joblib.load("/models/transaction_anomaly_detector/2/model.pkl")
        pb_utils.Logger.log_info(
            f"model initialized, args:{args}"
            f"numpy{ numpy.__version__}"
            f"scikit{ sklearn.__version__}"
        )

    def execute(self, requests):
        responses = []

        for request in requests:

            pb_utils.Logger.log_info(
                f"request {request}"
            )

            input_tensor = pb_utils.get_input_tensor_by_name(
                request,
                "INPUT"
            )

            values = input_tensor.as_numpy()
            # numerical python, -> array([[amount]], dtype=float32)

            pb_utils.Logger.log_info(
                f"value {values}"
                f"value shape={values.shape}"
            )

            prediction =self.model.predict(values)
            prediction_result = np.where(prediction == -1,
                              1,
                              0).astype(np.int32)

            pb_utils.Logger.log_info(
                f"prediction={prediction} "
                f"prediction_result={prediction_result} "
                f"prediction_result shape={prediction_result.shape} "
                f"prediction_result dtype={prediction_result.dtype} "
                f"prediction_result ndim={prediction_result.ndim} "
            )

            output_tensor = pb_utils.Tensor(
                "OUTPUT",
                prediction_result
            )

            score = self.model.decision_function(values)
            score_result = score.astype(np.float32)

            pb_utils.Logger.log_info(
                f"score={score} "
                f"score_result={score_result} "
                f"score_result shape={score_result.shape} "
                f"score_result dtype={score_result.dtype} "
                f"score_result ndim={score_result.ndim} "
            )
            score_tensor = pb_utils.Tensor(
                "SCORE",
                score_result
            )

            responses.append(
                pb_utils.InferenceResponse(
                    output_tensors = [
                        output_tensor,
                        score_tensor
                    ]
                )
            )
        return responses

