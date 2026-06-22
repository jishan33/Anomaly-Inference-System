import numpy as np
import triton_python_backend_utils as pb_utils

class TritonPythonModel:
    def initialize(self, args):
        print("anomaly_detector initialized")

    def execute(self, requests):

        responses = []

        for request in requests:
            input_tensor = pb_utils.get_input_tensor_by_name(
                request,
                "INPUT"
            )
            values = input_tensor.as_numpy()
            result = (values > 1000).astype(np.int32)
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