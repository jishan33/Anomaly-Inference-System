# Triton Model Serving

## Overview

The platform separates request orchestration from model execution using NVIDIA Triton Inference Server.

Triton acts as the dedicated model serving layer, allowing workers to focus on queue processing, request scheduling, and inference orchestration while delegating model loading, batching, and execution to a centralized serving infrastructure.

---

# Serving Architecture

```text
                Worker

                   │

             Model Routing

                   │

                   ▼

       Triton Inference Server

        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼

Transaction              Volume
Anomaly Detector     Anomaly Detector

        │                     │
        └──────────┬──────────┘
                   ▼

            Model Versioning
             (v1, v2, ...)
```

---

# Triton Responsibilities

Triton is responsible for:

- Model loading
- Request scheduling
- Dynamic batching
- Model version management
- Tensor validation
- Model execution

Workers communicate with Triton through the HTTP inference API and do not load model artifacts locally.

---

# Multi-Model Serving

## Overview

The platform supports serving multiple logical models from a single Triton deployment.

Although the project currently serves two lightweight models, the same architecture scales naturally to production AI platforms
that host dozens or hundreds of models.

Externalizing model selection through runtime configuration allows new models to be introduced without changing inference logic,
while Triton provides centralized model management, versioning, and observability.

---

## Current models

| Model | Purpose |
|--------|---------|
| `transaction_anomaly_detector` | Detect anomalous transactions |
| `volume_anomaly_detector` | Detect abnormal transaction volume |

---

## Runtime Model Routing

Model selection is externalized through Kubernetes configuration.

```yaml
ANOMALY_MODEL: transaction_anomaly_detector
```

Changing the target model only requires updating the Kubernetes ConfigMap.

No application code changes are required.

This approach enables:

- Independent model lifecycle management
- Per-model observability
- Per-model versioning
- Centralized model serving
- Simplified deployment

---
## Multi-Model Serving Trade-offs

### Benefits

- Centralized model serving
- Independent model lifecycle
- Shared serving infrastructure
- Simplified worker implementation

### Trade-offs
- Increase memory usage as additional models are loaded
- Resource contention between concurrently served models
- More complex capacity planning
- Per-model monitoring and autoscaling become increasingly important


# Model Versioning

Each model maintains its own version history.

```text
model_repository/

├── transaction_anomaly_detector/
│   ├── 1/
│   ├── 2/
│   └── config.pbtxt
│
└── volume_anomaly_detector/
    ├── 1/
    └── config.pbtxt
```

Workers specify both the model name and model version at inference time.

This allows:

- Canary deployments
- Shadow traffic validation
- Safe model promotion
- Rapid rollback

without modifying application code.

---

# Python Backend

The project uses Triton's Python Backend.

Each model implements the Triton lifecycle methods:

- `initialize()`
- `execute()`

The Python Backend enables custom preprocessing and postprocessing while leveraging Triton's serving infrastructure.

---

# Dynamic Batching

Dynamic batching is configured using:

- `max_batch_size`
- `preferred_batch_size`
- `max_queue_delay_microseconds`

Benefits:

- Improved throughput
- Reduced execution count
- Better compute utilization

Trade-offs:

- Slight increase in request latency
- Higher queue latency under light workloads

---

# Runtime Metadata

Workers retrieve model metadata directly from Triton instead of maintaining local model information.

This makes Triton the runtime source of truth for:

- Available model versions
- Model metadata
- Serving status

---

# Latency Decomposition

Triton exposes fine-grained latency metrics, enabling detailed performance analysis.

Metrics include:

- Queue latency
- Compute input latency
- Compute inference latency
- Compute output latency
- Request latency

Combined with worker-side metrics, these measurements provide complete end-to-end latency decomposition across the inference pipeline.