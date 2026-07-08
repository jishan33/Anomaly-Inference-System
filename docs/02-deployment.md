# Deployment

## Overview

The Anomaly Inference System supports both local development and Kubernetes deployment.

Two deployment environments are provided:

| Environment | Purpose |
|-------------|---------|
| Docker Compose | Local development and functional testing |
| Kubernetes | Production-style deployment, scaling, and observability |

---

# Local Development

The project can be started locally using Docker Compose.

Components deployed locally include:

```text
FastAPI

Redis

NGINX

Prometheus

Grafana

Triton Inference Server
```

Launch the platform:

```bash
docker compose up --build
```

---

# Kubernetes Deployment

The production deployment runs entirely on Kubernetes.

Major workloads include:

```text
FastAPI Deployment

VIP Worker Deployment

Shared Worker Deployment

Redis Deployment

Triton Deployment

Prometheus

Grafana

kube-state-metrics
```

Deployment manifests are located in:

```text
k8s/
```

---

# Kubernetes Architecture

```text
                    Kubernetes Cluster

            ┌─────────────────────────┐
            │      FastAPI API        │
            └─────────────┬───────────┘
                          │
                          ▼
                   Redis Service
                          │
          ┌───────────────┴───────────────┐
          │                               │
          ▼                               ▼
 VIP Worker Deployment         Shared Worker Deployment
          │                               │
          └───────────────┬───────────────┘
                          ▼
                  Triton Deployment
                          │
                          ▼
                     AI Model
```

---

# Kubernetes Resources

The project uses the following Kubernetes resources.

| Resource | Purpose |
|----------|---------|
| Deployment | Manage application replicas |
| Service | Internal service discovery |
| ConfigMap | Runtime configuration |
| Secret | Sensitive configuration |
| HPA | CPU-based autoscaling |
| KEDA ScaledObject | Inference-aware autoscaling |

---

# Service Discovery

Services communicate using Kubernetes DNS.

Examples:

```text
redis.default.svc.cluster.local

triton.default.svc.cluster.local

prometheus-service.default.svc.cluster.local
```

Workers communicate with Triton through the internal ClusterIP Service.

---

# Configuration Management

Runtime configuration is managed through Kubernetes ConfigMaps.

Examples include:

```text
Worker concurrency

Model rollout mode

Stable model version

Candidate model version

Canary percentage

Batch size

Redis configuration
```

Configuration changes can be applied without rebuilding container images.

---

# Health Probes

FastAPI exposes dedicated health endpoints.

```text
/livez

/readyz
```

These endpoints are used by Kubernetes:

- Liveness Probe
- Readiness Probe

to detect unhealthy Pods and remove them from service automatically.

---

# Scaling Strategy

Different workloads scale independently.

| Component | Scaling Strategy |
|----------|------------------|
| FastAPI | Horizontal Pod Autoscaler |
| Workers | KEDA multi-signal autoscaling |
| Triton | KEDA inference-aware autoscaling |

This allows API handling, request processing, and model serving capacity to scale independently.

---

# Deployment Workflow

The typical deployment process is:

```text
Train Model

↓

Package Model

↓

Build Docker Images

↓

Push Images (Production)

↓

Deploy Kubernetes Manifests

↓

Verify Health

↓

Run Load Tests

↓

Observe Grafana Dashboards
```

---

# Deployment Validation

After deployment, the following checks are performed:

- All Pods are healthy
- Readiness probes pass
- Triton loads the model successfully
- Workers communicate with Redis and Triton
- Prometheus scrapes all targets
- Grafana dashboards display live metrics
- End-to-end inference succeeds

---

# Deployment Structure

```text
k8s/

├── app-*.yaml
├── worker-*.yaml
├── triton-*.yaml
├── redis-*.yaml
├── *-autoscaling.yaml
├── monitoring/
└── configmap.yaml
```

The manifests are organized by platform component to simplify deployment and maintenance.