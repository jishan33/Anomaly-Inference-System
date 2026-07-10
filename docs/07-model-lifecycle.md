# Model Registry and Artifact Management

The platform includes a lightweight model registry layer that tracks mode metadata separately from model serving.

Triton is responsible for executing model inference, while the model registry is responsible for describing which models exist, 
which versions are stable or candidate versions, and which aliases should be used by serving workloads.

This separation allows the platform to support safe model lifecycle operations such as promotion, rollback, canary deployment, 
and shadow validation without changing application code.

The registry tracks: 

- Model name
- Model owner
- Serving Backend
- Artifact path
- Model versions
- Model aliases
- Rollout eligibility
- Input contract 
- Output contract

Workers resolve logical aliases such as `stable`, `candidate`, `canary`, or `shadow` into physical Triton model versions 
before calling Triton.

This makes model routing safer and more production-like because serving code depends on stable logical aliases rather than
hardcoded model versions.