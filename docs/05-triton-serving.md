# Triton Model Serving

## Overview

The platform separates request orchestration from model execution using NVIDIA Triton Inference Server.

---

# Serving Architecture

```text
Worker

↓

Inference Client

↓

Triton

↓

IsolationForest
```

---

# Triton Responsibilities

- Model loading
- Dynamic batching
- Model version management
- Tensor validation
- Request scheduling

---

# Python Backend

The project uses Triton's Python Backend.

Each model implements:

- initialize()
- execute()

---

# Dynamic Batching

Configured through:

- max_batch_size
- preferred_batch_size
- max_queue_delay_microseconds

Benefits:

- Higher throughput
- Reduced execution count

Trade-offs:

- Slightly higher latency

---

# Model Repository

```text
model_repository/

anomaly_detector/

1/

2/

config.pbtxt
```

---

# Runtime Metadata

Workers retrieve model metadata directly from Triton instead of maintaining local model information.

---

# Latency Decomposition

Triton exposes:

- Queue latency
- Compute input latency
- Compute inference latency
- Compute output latency
- Request latency

These metrics enable detailed bottleneck analysis.