# Anomaly Inference System

Production-style AI inference platform demonstrating modern inference serving architecture using Kubernetes, Triton Inference Server, Redis, Prometheus, and Grafana.

---

# Overview

The project explores production AI serving concepts including:

- Queue-based asynchronous inference
- Multi-tenant QoS scheduling
- Dynamic batching
- Kubernetes-native deployment
- Inference-aware autoscaling
- Model versioning
- Canary deployment
- Shadow traffic
- Production observability

Built as part of an AI Infrastructure Engineer transition roadmap.


## Features

- Queue-based asynchronous inference
- Multi-tenant worker scheduling
- Adaptive batching
- Triton Inference Server
- Dynamic batching
- Kubernetes deployment
- KEDA autoscaling
- Model versioning
- Canary deployment
- Shadow traffic
- Prometheus
- Grafana

## Architecture
```Text
Client

↓

FastAPI

↓

Redis

↓

Worker

↓

Triton

↓

Model

↓

Prometheus / Grafana

```

## 🛠️ Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Programming Language** | Python |
| **API Layer** | FastAPI, Pydantic |
| **AI Model** | Scikit-learn (IsolationForest) |
| **Inference Serving** | Triton Inference Server (Python Backend) |
| **Model Serving** | Dynamic Batching, Model Versioning, Canary Deployment, Shadow Traffic |
| **Queue & Messaging** | Redis |
| **Worker Processing** | Asynchronous Worker Pool, QoS Scheduling |
| **Containerization** | Docker |
| **Container Orchestration** | Kubernetes |
| **Autoscaling** | Horizontal Pod Autoscaler (HPA), KEDA |
| **Observability** | Prometheus, Grafana |
| **Infrastructure Metrics** | cAdvisor, kube-state-metrics, NGINX Exporter |
| **Networking** | NGINX, Kubernetes Services |
| **Configuration** | Kubernetes ConfigMaps |
| **Load Testing** | Custom concurrent load testing scripts |


## Production Capabilities

- Queue-based asynchronous inference
- Worker pools
- Kubernetes orchestration
- Dynamic batching
- Triton model serving
- Inference-aware autoscaling
- Model versioning
- Canary deployment
- Shadow traffic
- Production observability

Detailed implementation is documented in `/docs`.


## Quick Start

```bash
train model

docker compose up

kubectl apply
```

## Documentation

| Topic | Description |
|--------|-------------|
| architecture.md | Overall platform architecture |
| deployment.md | Docker and Kubernetes deployment |
| observability.md | Metrics and monitoring |
| autoscaling.md | HPA, KEDA, inference-aware autoscaling |
| triton-serving.md | Triton integration and dynamic batching |
| model-rollout.md | Model versioning, canary, shadow traffic |
| dashboards.md | Grafana dashboards |


## Repository Structure

```text
Anomaly-Inference-System/
│
├── app/                 # Inference API & worker services
├── triton/              # Model serving
├── k8s/                 # Kubernetes infrastructure
├── dashboards/          # Grafana dashboards
├── docs/                # Engineering documentation
├── scripts/             # Training & utilities
├── models/              # Training artifacts
│
├── README.md
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```