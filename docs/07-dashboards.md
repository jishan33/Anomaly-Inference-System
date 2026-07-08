# Dashboards

## Overview

The Anomaly Inference System includes multiple Grafana dashboards that provide visibility into platform health, inference performance, autoscaling behaviour, and model rollout.

The dashboards are designed around operational workflows rather than individual components.

Their objectives are to:

- Detect production incidents
- Identify system bottlenecks
- Understand inference latency
- Validate autoscaling behaviour
- Monitor model rollouts
- Compare model behaviour during shadow traffic

---

# Dashboard Architecture

```text
Application
      │
Worker
      │
Redis
      │
Triton
      │
Kubernetes
      │
Prometheus
      │
Grafana
```

---

# 1. API & Application Dashboard

Purpose

Monitor API health and client-facing performance.

Key Panels

| Panel | Purpose |
|--------|---------|
| Request Rate | Incoming traffic volume |
| Request Latency (P95) | Client-facing latency |
| Error Rate | HTTP and application failures |
| Request Shedding | Backpressure effectiveness |
| User Rate Limiting | Admission control behaviour |

Operational Questions

- Is the API healthy?
- Are clients experiencing higher latency?
- Is traffic exceeding platform capacity?

---

# 2. Queue & Worker Dashboard

Purpose

Monitor asynchronous request processing.

Key Panels

| Panel | Purpose |
|--------|---------|
| Queue Depth | Outstanding inference jobs |
| Queue Wait Time (P95) | Queue congestion |
| Worker Processing Latency (P95) | Worker execution performance |
| Processed Request Rate | Worker throughput |
| Active Workers | Current processing capacity |
| Adaptive Batch Size | Worker batching behaviour |
| Adaptive Batch Timeout | Worker batching strategy |

Operational Questions

- Is the queue growing?
- Are workers keeping up with demand?
- Should additional workers be provisioned?

---

# 3. Triton Inference Dashboard

Purpose

Monitor model serving performance.

Key Panels

| Panel | Purpose |
|--------|---------|
| Request Rate | Inference throughput |
| Request Latency | End-to-end Triton latency |
| Queue Latency | Waiting inside Triton |
| Compute Input Latency | Tensor preparation |
| Compute Inference Latency | Model execution |
| Compute Output Latency | Response generation |
| Execution Count | Dynamic batching efficiency |
| Queue Ratio | Queueing pressure |
| Effective Batch Size | Dynamic batching behaviour |

Operational Questions

- Is Triton becoming the bottleneck?
- Is dynamic batching effective?
- Which stage contributes most to latency?

---

# 4. Infrastructure Dashboard

Purpose

Monitor Kubernetes cluster health.

Key Panels

| Panel | Purpose |
|--------|---------|
| CPU Utilization | Resource saturation |
| Memory Utilization | Memory pressure |
| Pod Status | Application health |
| Replica Count | Scaling behaviour |
| Network Traffic | Communication health |

Operational Questions

- Is the cluster healthy?
- Which workload is resource constrained?
- Has autoscaling completed successfully?

---

# 5. Autoscaling Dashboard

Purpose

Validate inference-aware autoscaling decisions.

## Worker Autoscaling

Signals

- Redis Queue Depth
- Worker Processing Latency
- CPU Utilization

## Triton Autoscaling

Signals

- Triton Request Latency
- Triton Queue Latency
- CPU Utilization

Key Panels

| Panel | Purpose |
|--------|---------|
| Worker Replicas | Worker scaling behaviour |
| Triton Replicas | Triton scaling behaviour |
| Queue Depth | Scaling trigger |
| Queue Latency | Inference bottleneck |
| Worker Processing Latency | Worker bottleneck |
| CPU Utilization | Resource pressure |

Operational Questions

- Which component should scale?
- Is KEDA responding correctly?
- Are scaling decisions reducing latency?

---

# 6. Reliability Dashboard

Purpose

Monitor platform resilience.

Key Panels

| Panel | Purpose |
|--------|---------|
| Circuit Breaker State | Dependency health |
| Retry Attempts | Retry behaviour |
| Redis Failures | Backend failures |
| DLQ Jobs | Failed inference requests |
| DLQ Push Failures | Reliability issues |

Operational Questions

- Are dependencies healthy?
- Are retries increasing?
- Is the platform degrading gracefully?

---

# 7. Model Rollout Dashboard

Purpose

Validate candidate models before promotion.

Key Panels

| Panel | Purpose |
|--------|---------|
| Request Rate by Model Version | Traffic distribution |
| Prediction Agreement | Stable vs Candidate agreement |
| Prediction Disagreement | Behaviour differences |
| Prediction Score Difference (P95) | Score drift |
| Prediction Distribution | Anomaly rate by version |
| Prediction Score Distribution (P95) | Score distribution by version |

Operational Questions

- Are both models behaving similarly?
- Has prediction behaviour changed?
- Can the candidate model be promoted?

---

# Dashboard Design Philosophy

The dashboards follow the operational lifecycle of an AI inference platform.

```text
Client Requests
        │
API Health
        │
Queue Health
        │
Worker Performance
        │
Inference Performance
        │
Infrastructure Health
        │
Autoscaling
        │
Model Validation
```

Rather than presenting isolated infrastructure metrics, the dashboards provide a complete operational view of the platform from request admission through model execution and production rollout.