# Anomaly Inference System

A production-style AI inference platform demonstrating modern model serving, inference infrastructure, and distributed systems using **Kubernetes**, **Triton Inference Server**, **Redis**, **Prometheus**, and **Grafana**.

Built as part of an **AI Infrastructure Engineer** transition roadmap to explore production AI serving patterns, observability, autoscaling, and model rollout strategies.

## 🎯 Engineering Focus

- AI Inference Platform
- Kubernetes & Cloud-Native Infrastructure
- Triton Inference Server
- Inference-Aware Autoscaling
- Production Observability
- Model Versioning & Rollouts

---

# 🚀 Platform Capabilities

* Queue-based asynchronous inference
* Multi-tenant worker scheduling
* Triton Inference Server integration
* Dynamic batching
* Kubernetes-native deployment
* Inference-aware autoscaling (KEDA & HPA)
* Model versioning
* Canary deployment
* Shadow traffic validation
* Production observability

---

# 🏗️ High-Level Architecture

```text
                Client
                   │
                   ▼
              FastAPI API
                   │
                   ▼
          Redis Request Queue
                   │
                   ▼
           Worker Pool (QoS)
                   │
                   ▼
      Triton Inference Server
                   │
                   ▼
          ML Model Repository
                   │
                   ▼
      Prometheus + Grafana
```

---

# 🛠️ Technology Stack

| Category                   | Technologies                                                          |
| -------------------------- | --------------------------------------------------------------------- |
| **Language**               | Python                                                                |
| **API**                    | FastAPI, Pydantic                                                     |
| **Machine Learning**       | Scikit-learn (IsolationForest)                                        |
| **Inference Serving**      | Triton Inference Server (Python Backend)                              |
| **Model Serving**          | Dynamic Batching, Model Versioning, Canary Deployment, Shadow Traffic |
| **Messaging**              | Redis                                                                 |
| **Worker Processing**      | Asynchronous Worker Pool, QoS Scheduling                              |
| **Containerization**       | Docker                                                                |
| **Orchestration**          | Kubernetes                                                            |
| **Autoscaling**            | KEDA, Horizontal Pod Autoscaler (HPA)                                 |
| **Observability**          | Prometheus, Grafana                                                   |
| **Infrastructure Metrics** | cAdvisor, kube-state-metrics, NGINX Exporter                          |
| **Networking**             | NGINX, Kubernetes Services                                            |
| **Configuration**          | Kubernetes ConfigMaps                                                 |
| **Testing**                | Custom concurrent load-testing scripts                                |

---

# ⚡ Quick Start

```bash
# Train the model
python scripts/train_model.py

# Start local services
docker compose up

# Deploy to Kubernetes
kubectl apply -f k8s/
```

---

# 📚 Documentation

| Document               | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| `01-architecture.md`   | Platform architecture and request flow                  |
| `02-deployment.md`     | Docker and Kubernetes deployment                        |
| `03-observability.md`  | Metrics, monitoring, and operational visibility         |
| `04-autoscaling.md`    | HPA, KEDA, and inference-aware autoscaling              |
| `05-triton-serving.md` | Triton integration and dynamic batching                 |
| `06-model-rollout.md`  | Model versioning, canary deployment, and shadow traffic |
| `07-dashboards.md`     | Grafana dashboards and platform validation              |

---

# 📂 Repository Structure

```text
Anomaly-Inference-System/
│
├── app/                  # API, workers, and shared components
├── triton/               # Triton model repository
├── k8s/                  # Kubernetes manifests
├── dashboards/           # Grafana dashboards
├── docs/                 # Engineering documentation
├── scripts/              # Model training and utilities
├── models/               # Training artifacts
│
├── README.md
├── Dockerfile
├── docker-compose.yaml
└── requirements.txt
```
