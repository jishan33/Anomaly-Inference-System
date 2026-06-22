# Day 38 — Triton Inference Server Concepts

## Goal

Understand why production inference systems often use a dedicated model-serving runtime instead of executing models directly inside application workers.

## Current System

```text
Client
 ↓
FastAPI API Layer
 ↓
Redis Queue
 ↓
VIP / Shared Workers
 ↓
ModelRuntime wrapper
 ↓
model.pkl + metadata.json
 ↓
IsolationForest
```

## Triton-Style System

```Text
Client
 ↓
FastAPI API Layer
 ↓
Redis Queue / Request Router
 ↓
VIP / Shared Workers
 ↓
Triton Inference Server
 ↓
Model Repository
 ↓
Model Backend
 ↓
CPU / GPU
```

## Key Difference

In the current system, the worker owns model execution.

In a Triton-style system, the worker becomes an inference client. Triton owns model loading, model execution,
batching, backend runtime, and model-serving metrics.

## Triton's Five Core Ideas

### 1. Model Repository
Triton serves models from a model repository.

Example structure:
```text
model_repository/
└── anomaly_detector/
    ├── config.pbtxt
    └── 1/
        └── model.onnx
```

This is similar to my current structure:
```text
models/
└── anomaly-detector/
    └── v1/
        ├── model.pkl
        └── metadata.json
```
But Triton standardizes this format so the inference server can load and serve models consistently.

### 2. config.pbtxt
`config.pbtxt` describes how Triton should serve the model.

It can define:
- model name
- backend/platform
- max batch size 
- input tensors
- output tensors
- dynamic batching
- model instance count

### 3. Backend
A backend is the runtime that executes the model.

Examples:
- ONNX Runtime
- TensorRT
- PyTorch
- TensorFlow
- Python backend

My current sklearn `IsolationForest` is not a natural Triton GPU model, but a future ONNX, PyTorch,
or TensorRT model would fit better.

### 4. Dynamic Batching
Triton can combine multiple inference requests into a batch internally.

My current system implements batching in the worker.

Triton moves batching into the model-serving runtime.

### 5. Model Instances
Triton can run multiple instances of the same model to increase concurrency.

Kubernetes replicas scale pods.

Triton model instances scale model execution inside a Triton server process.

## Compare Current System vs Triton-Style System

| Concern | Current System | Triton-Style System |
|---|---|---|
| Model loading | `model.py` loads `model.pkl` | Triton loads model repository |
| Model metadata | `metadata.json` | `config.pbtxt` + model repository version |
| Batching | worker batching logic | dynamic batching inside Triton |
| Runtime execution | Python/sklearn | backend-specific runtime |
| Model versioning | `models/anomaly-detector/v1` | `model_repository/anomaly_detector/1` |
| Inference API | FastAPI endpoints | Triton HTTP/gRPC inference API |
| Worker role | executes model | calls Triton |
| Scaling | Kubernetes pods + workers | Kubernetes pods + Triton model instances |
| Observability | custom Prometheus metrics | app metrics + Triton metrics |

## Metrics Mapping

### Application / Worker Metrics

These remain in my system:

- queue wait latency
- worker processing latency
- 503 rate
- queue depth
- tenant/tier throughput
- circuit breaker state
- pod restarts
- Redis failure behavior

### Model Runtime Metrics

These would move closer to Triton:

- model inference request count
- model inference latency
- model batch size
- model load time
- model version / model name
- model runtime/backend

## Day 38 Key Learning

My current Day 37 introduce model artifact loading and model-runtime metrics inside the worker.
Triton represents the next production step: separate model execution from application orchestration.
The worker should not always execute the model directly. For larger models, the worker can become a client that sends
inference requests to a dedicated model-serving runtime. This allows the serving runtime to specialize in model loading,
batching, backend execution, concurrency, and runtime observability.