# Autoscaling

## Overview

The platform independently scales API servers, workers, and Triton inference servers.

Each workload scales using signals relevant to its responsibilities.

---

# Scaling Architecture

```text
FastAPI

↓

Workers

↓

Triton
```

Each layer scales independently.

---

# Worker Autoscaling

KEDA monitors:

- Redis queue depth
- Worker processing latency
- CPU utilization

Purpose:

Increase request processing capacity when the inference queue grows.

---

# Triton Autoscaling

KEDA monitors:

- Triton request latency
- Triton queue latency
- CPU utilization

Purpose:

Increase inference capacity when model execution becomes the bottleneck.

---

# Inference-Aware Scaling

Unlike CPU-only autoscaling, inference-aware autoscaling considers serving-specific metrics.

Examples include:

- Queue latency
- Request latency
- Queue depth
- Processing latency
- Dynamic batching efficiency

---

# Trade-offs

Worker scaling:

Advantages

- Faster queue draining
- Better throughput

Disadvantages

- Increased Triton load

---

Triton scaling:

Advantages

- Lower inference latency
- Higher inference throughput

Disadvantages

- Increased infrastructure cost

---

# Scaling Decision Matrix

| Observation | Action |
|-------------|--------|
| Queue growing, worker latency increasing | Scale workers |
| Triton queue latency increasing | Scale Triton |
| CPU saturation | Scale affected workload |