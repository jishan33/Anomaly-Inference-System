import joblib
import numpy
import numpy as np
import sklearn
import triton_python_backend_utils as pb_utils

class TritonPythonModel:
    def initialize(self, args):
        self.model = joblib.load("/models/anomaly_detector/1/model.pkl")
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
            pb_utils.Logger.log_info(
                f"input_tensor {input_tensor}"
                f"input_tensor shape={input_tensor.shape}"
            )

            values = input_tensor.as_numpy()
            # numerical python, -> array([[amount]], dtype=float32)

            pb_utils.Logger.log_info(
                f"value {values}"
                f"value shape={values.shape}"
            )

            prediction =self.model.predict(values)
            pb_utils.Logger.log_info(f" prediction shape={prediction.shape}")

            result = np.where(prediction == -1,
                              1,
                              0).astype(np.int32)

            pb_utils.Logger.log_info(
                f"result={result} "
                f"result shape={result.shape} "
                f"result dtype={result.dtype} "
                f"result ndim={result.ndim} "
            )

            output_tensor = pb_utils.Tensor(
                "OUTPUT",
                result
            )

            responses.append(
                pb_utils.InferenceResponse(
                    output_tensors = [output_tensor]
                )
            )
        return responses

