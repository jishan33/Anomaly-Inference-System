# Architecture

## Overview

The Anomaly Inference System is a production-style AI inference platform that demonstrates modern inference serving patterns using asynchronous processing, Kubernetes-native deployment, Triton Inference Server, inference-aware autoscaling, and production observability.

The platform is designed to decouple API handling, request scheduling, model execution, and infrastructure operations to improve scalability, resilience, and maintainability.

---

# High-Level Architecture

```text
                           Kubernetes Cluster

                        ┌────────────────────────┐
                        │      FastAPI API       │
                        │                        │
                        │  Request Validation    │
                        │  Rate Limiting         │
                        │  Health Endpoints      │
                        └────────────┬───────────┘
                                     │
                                     ▼
                           ┌─────────────────┐
                           │     Redis       │
                           │ Inference Queue │
                           └────────┬────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
                  ▼                                   ▼
         VIP Worker Deployment              Shared Worker Deployment
                  │                                   │
                  └───────────────┬───────────────────┘
                                  │
                        QoS Scheduling & Batching
                                  │
                                  ▼
                    Triton Inference Server
                                  │
                    Dynamic Batching
                    Model Versioning
                    Canary Deployment
                    Shadow Traffic
                                  │
                                  ▼
                       IsolationForest Models
                           Version 1 / Version 2

────────────────────────────────────────────────────────────

 Prometheus
        │
 Grafana
```

---

# Design Principles

The platform follows several production AI infrastructure principles.

## Separation of Responsibilities

The inference pipeline separates request handling from model execution.

```text
Client

↓

FastAPI

↓

Redis Queue

↓

Worker

↓

Triton

↓

Model
```

Each component owns a single responsibility:

| Component | Responsibility |
|------------|----------------|
| FastAPI | Request validation, admission control, asynchronous job submission |
| Redis | Queue buffering and result storage |
| Worker | Queue consumption, QoS scheduling, inference orchestration |
| Triton | Model loading, batching, model execution |
| Prometheus | Metrics collection |
| Grafana | Visualization and operational monitoring |

---

# Request Lifecycle

```text
Client

↓

POST /predict_async

↓

Validate request

↓

Push job to Redis

↓

Worker dequeues request

↓

Preprocess features

↓

Triton inference

↓

Postprocess prediction

↓

Store result in Redis

↓

Client polls /result/{job_id}
```

---

# Inference Pipeline

The worker performs inference in three logical stages:

```text
Feature Extraction

↓

Inference Client

↓

Post Processing
```

The inference client further separates:

```text
Preprocess Input

↓

Run Triton Inference

↓

Postprocess Output
```

This separation keeps Triton-specific logic isolated from business logic.

---

# Worker Architecture

Workers are stateless.

Responsibilities include:

- Queue consumption
- QoS scheduling
- Request batching
- Triton communication
- Result persistence
- Metrics collection

Workers do not perform model loading.

---

# Model Serving

Model execution is delegated to Triton Inference Server.

Benefits include:

- Centralized model management
- Dynamic batching
- Runtime model versioning
- Standardized inference API
- Dedicated serving infrastructure

Worker and model execution are independently scalable.

---

# Deployment Architecture

The platform is deployed on Kubernetes.

Major workloads include:

- FastAPI Deployment
- Shared Worker Deployment
- VIP Worker Deployment
- Triton Deployment
- Redis Deployment
- Prometheus
- Grafana

Infrastructure configuration is managed through Kubernetes manifests and ConfigMaps.

---

# Production AI Serving Features

Current platform capabilities include:

- Queue-based asynchronous inference
- Multi-tenant worker scheduling
- QoS request prioritization
- Dynamic batching
- Kubernetes-native deployment
- Horizontal Pod Autoscaling
- KEDA inference-aware autoscaling
- Triton model serving
- Model versioning
- Canary deployment
- Shadow traffic
- Production observability

---

# Design Goals

The project emphasizes production AI serving patterns rather than model development.

Primary objectives include:

- Decoupled inference architecture
- Scalable request processing
- Production observability
- Infrastructure resilience
- Safe model deployment
- Operational simplicity
- AI infrastructure best practices