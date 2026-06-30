# Anomaly Inference System

Production-style AI inference infrastructure project focused on queue-based inference, adaptive batching, QoS scheduling, autoscaling, Kubernetes reliability, model-serving observability, and production AI serving patterns.

---

# 🚀 Overview

This project simulates a production AI inference platform with:

* Multi-tenant request isolation
* VIP vs Free-tier scheduling
* Queue-based asynchronous inference
* Adaptive batching
* Elastic worker orchestration
* Kubernetes-based deployment
* Horizontal Pod Autoscaling
* Model artifact loading
* Model metadata exposure
* Full observability stack
* Infrastructure saturation analysis
* Reliability and failure recovery testing

The system was built as part of an AI Infrastructure Engineer transition roadmap focused on distributed systems, ML serving infrastructure, inference platform engineering, Kubernetes operations, and production observability.

---

# 🏗️ System Architecture

```text
Client
   │
   ▼
Nginx / Kubernetes Service
   │
   ▼
FastAPI API Layer
   │
   ▼
Redis Queue Layer
 ┌───────────────┐
 │ VIP Queue     │
 │ Free Queue    │
 └───────────────┘
   │
   ▼
Worker Pools
 ┌────────────────┐
 │ VIP Workers    │
 │ Shared Workers │
 └────────────────┘
   │
   ▼
Model Runtime Wrapper
   │
   ▼
Model Artifact
 ┌──────────────────────────────┐
 │ model.pkl                    │
 │ metadata.json                │
 │ model_name / version/runtime │
 └──────────────────────────────┘
   │
   ▼
Inference Model
(Isolation Forest)

--------------------------------

Observability Stack

Prometheus
   ▲
   │
Grafana Dashboards

kube-state-metrics
cadvisor
nginx-exporter
worker metrics
application metrics
model runtime metrics
autoscaler metrics
```

---

# 🚀 Core Features

## Queue-Based Inference

Requests are decoupled from inference execution using Redis-backed queues.

### Endpoints

| Endpoint           | Purpose                         |
| ------------------ | ------------------------------- |
| `/predict`         | synchronous inference           |
| `/predict_async`   | enqueue async inference job     |
| `/result/{job_id}` | retrieve async inference result |
| `/model_metadata`  | query loaded model metadata     |
| `/livez`           | liveness probe                  |
| `/readyz`          | readiness probe                 |
| `/metrics`         | Prometheus metrics              |

---

# 🚀 Model Artifact Loading

The project now separates **training** from **serving**.

Training creates a model artifact:

```text
scripts/train_model.py
   │
   ▼
models/anomaly-detector/v1/model.pkl
models/anomaly-detector/v1/metadata.json
```

Serving loads the pre-trained artifact instead of training the model on application startup.

This models the production AI serving pattern:

```text
Training pipeline
   │
   ▼
Model artifact
   │
   ▼
Serving runtime
   │
   ▼
Inference
```

## Manual Training Before Deploy

For the current learning-stage implementation, model training is triggered manually before deployment:

```bash
python3 scripts/train_model.py
```

This generates:

```text
models/anomaly-detector/v1/model.pkl
```

The serving application then loads the artifact at startup.

---

# 🚀 Model Metadata

Each model version includes a `metadata.json` file describing the loaded model.

Example:

```json
{
  "model_name": "anomaly-detector",
  "model_version": "v1",
  "model_runtime": "sklearn",
  "feature_schema_version": "v1"
}
```

The model metadata is exposed through:

```text
/model_metadata
```

This helps verify:

* which model version is loaded
* which runtime is serving predictions
* whether all pods loaded the expected model
* whether model rollout behavior is correct

Model metadata is used for observability and debugging, not business logic.

---

# 🚀 QoS Scheduling

The system supports:

* VIP-tier prioritization
* Shared worker overflow handling
* Multi-tenant fairness
* Queue isolation

VIP traffic can receive:

* lower latency
* faster scheduling
* dedicated worker capacity

---

# 🚀 Adaptive Batching

Batching dynamically adjusts based on:

* queue pressure
* workload intensity
* latency considerations

The scheduler tunes:

* batch size
* batch wait timeout

Tradeoffs explored:

* throughput vs latency
* GPU efficiency simulation
* queue buildup behavior
* batching impact on tail latency
* tier-specific batching behavior

---

# 🚀 Autoscaling

The system supports autoscaling behavior through both application-level worker elasticity and Kubernetes HPA.

Autoscaling signals explored include:

* CPU usage
* queue depth
* queue wait latency
* worker processing latency
* desired vs available replicas
* scale-up lag
* scale-down behavior

Key learning:

```text
CPU alone is not enough for inference autoscaling.

Production inference autoscaling should consider:
CPU + queue depth + latency + model/runtime saturation.
```

---

# 🚀 Observability Stack

## Prometheus

Metrics collection across:

* FastAPI apps
* workers
* autoscaler
* nginx
* cadvisor
* kube-state-metrics
* model runtime

---

## Grafana Dashboards

Dashboards include:

### Traffic

* ingress throughput
* processed throughput
* free-tier throughput ratio

### Queue

* queue depth
* queue wait latency P95
* queue pressure ratio

### Workers

* worker processing latency
* worker occupancy
* active worker state
* active worker counts

### Model Runtime

* model inference throughput
* model inference latency P95
* model version labels
* model runtime labels

### Model Lifecycle

* model load time
* model load count
* model metadata visibility

### Batching

* configured batch timeout
* model batch size P95
* average batch size

### Reliability

* 503 rate
* pod restarts
* circuit breaker state
* Redis outage behavior

### Infrastructure

* CPU usage
* memory usage
* container count
* nginx metrics
* Kubernetes replica state

---

# 🚀 Model Inference Dashboard

The model inference dashboard is organized into production-style rows:

```text
Model Runtime
Model Lifecycle
Queue + Worker
Batching
Reliability
```

Important panels:

| Panel                         | Purpose                                      |
| ----------------------------- | -------------------------------------------- |
| Model Inference Throughput    | inference request rate by tier/version       |
| Model Inference Latency P95   | model execution latency                      |
| Model Load Count              | verifies each pod loaded the model           |
| Model Load Time               | tracks cold-start model loading cost         |
| Queue Wait Latency P95        | measures queue delay before worker execution |
| Worker Processing Latency P95 | measures worker-side processing time         |
| Configured Batch Timeout      | shows active batching timeout config         |
| Model Batch Size P95          | shows upper-end batch size behavior          |
| Average Batch Size            | shows normal batching behavior               |
| 503 Rate                      | user-facing service failure signal           |
| Pod Restarts Last 1h          | recent Kubernetes instability signal         |

---

# 🚀 Infrastructure Components

| Component          | Purpose                          |
| ------------------ | -------------------------------- |
| FastAPI            | inference API                    |
| Redis              | queue + coordination             |
| Nginx              | ingress + load balancing         |
| Prometheus         | metrics collection               |
| Grafana            | observability dashboards         |
| cadvisor           | container infrastructure metrics |
| kube-state-metrics | Kubernetes state metrics         |
| nginx-exporter     | nginx Prometheus exporter        |
| Kubernetes HPA     | pod autoscaling                  |

---

# 🚀 Scaling & Systems Concepts Explored

This project intentionally explores real infrastructure tradeoffs:

* oversubscription
* CPU saturation
* queue buildup
* latency vs throughput
* adaptive batching
* autoscaling stability
* worker elasticity
* ingress backpressure
* Kubernetes pod lifecycle
* failure recovery
* model cold start
* model artifact loading
* model-serving observability
* observability-driven debugging

---

# 🚀 Running The System

## Train Model Artifact

Run this before building/deploying the serving system:

```bash
python3 scripts/train_model.py
```

This creates:

```text
models/anomaly-detector/v1/model.pkl
```

---

## Start Infrastructure With Docker Compose

```bash
docker compose up --build
```

---

# 🚀 Access Services

| Service    | URL                   |
| ---------- | --------------------- |
| FastAPI    | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| Grafana    | http://localhost:3000 |
| cadvisor   | http://localhost:8080 |

---

# 🚀 Example Load Testing

Burst-based load testing was used to simulate:

* queue pressure
* saturation
* autoscaling events
* latency degradation
* worker failure
* Redis outage
* Kubernetes pod replacement
* model inference traffic

The project explores:

* worker oversubscription
* infrastructure bottlenecks
* throughput plateaus
* queue growth behavior
* model inference latency
* controlled failure recovery

---

# 🚀 Kubernetes Deployment

The system supports Kubernetes-based deployment for production-style orchestration and workload management.

## Kubernetes Concepts Explored

* Deployments
* Services
* ConfigMaps
* RBAC
* Replica orchestration
* Kubernetes Services
* EndpointSlice service discovery
* Self-healing infrastructure
* Declarative scaling
* Pod lifecycle management
* Health probes
* Horizontal Pod Autoscaling
* Kubernetes infrastructure metrics

---

# 🚀 Kubernetes Architecture

```text
Client
   │
   ▼
Kubernetes Service
   │
   ▼
FastAPI Pod Replicas
 ┌────────────────────────────┐
 │ anomaly-inference-system   │
 │ anomaly-inference-system   │
 └────────────────────────────┘
   │
   ▼
Redis Queue Layer
   │
   ▼
Worker Deployments
 ┌────────────────┐
 │ vip-worker     │
 │ shared-worker  │
 └────────────────┘
   │
   ▼
Model Runtime
   │
   ▼
Model Artifact
```

---

# 🚀 Kubernetes Deployment Features

The Kubernetes deployment supports:

* multi-pod inference serving
* service-level load balancing
* automatic pod recovery
* declarative replica scaling
* EndpointSlice-based service discovery
* worker deployment isolation
* pod-level Prometheus scraping
* liveness and readiness probes

---

# 🚀 Kubernetes Manifests

| Manifest                            | Purpose                         |
| ----------------------------------- | ------------------------------- |
| `k8s/app-deployment.yaml`           | FastAPI deployment              |
| `k8s/app-service.yaml`              | FastAPI Kubernetes Service      |
| `k8s/redis-deployment.yaml`         | Redis deployment                |
| `k8s/redis-service.yaml`            | Redis service                   |
| `k8s/vip-worker-deployment.yaml`    | VIP worker deployment           |
| `k8s/shared-worker-deployment.yaml` | Shared worker deployment        |
| `k8s/prometheus-configmap.yaml`     | Prometheus scrape configuration |
| `k8s/prometheus-deployment.yaml`    | Prometheus deployment           |
| `k8s/grafana-deployment.yaml`       | Grafana deployment              |
| `k8s/hpa.yaml`                      | Horizontal Pod Autoscaler       |

---

# 🚀 Example Kubernetes Commands

## Build Image

```bash
docker build -t anomaly-inference-system:latest .
```

## Deploy Application

```bash
kubectl apply -f k8s/
```

## Verify Resources

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get endpointslices
kubectl get hpa
```

## Restart Deployments After Shared Code Changes

```bash
kubectl rollout restart deployment/anomaly-inference-system
kubectl rollout restart deployment/vip-worker
kubectl rollout restart deployment/shared-worker
```

## Scale Deployment

```bash
kubectl scale deployment anomaly-inference-system --replicas=5
```

## Test Self-Healing

```bash
kubectl delete pod <pod-name>
```

Kubernetes automatically recreates failed pods to maintain the desired replica count.

---

# 🚀 Reliability Testing

Reliability tests performed:

* API pod deletion
* worker pod deletion
* Redis pod restart
* Redis outage by scaling Redis to zero
* long Redis outage
* frequent short Redis failure injection
* load testing during dependency failure

Key findings:

* Kubernetes recovers deleted pods automatically
* queues absorb short worker failures
* Redis is currently a single point of failure
* pod restarts can reset app counters
* severe outages may disappear from app metrics
* Kubernetes metrics are needed alongside application metrics
* stale worker pods can cause old metrics to remain visible

---

# 🚀 Observability Lessons

Important observability issues discovered:

* service scraping can corrupt metrics when multiple pods are behind one service
* pod scraping gives cleaner per-pod visibility
* multiprocess app metrics can create misleading counters
* stale pods can keep emitting old metrics
* app metrics alone are insufficient during severe outages
* model-serving dashboards need model, queue, worker, and Kubernetes signals together

---

# 🚀 Kubernetes Learning Outcomes

This phase explored:

* distributed workload orchestration
* control-plane reconciliation
* service discovery
* declarative infrastructure management
* containerized deployment workflows
* self-healing systems
* health checking
* Kubernetes-native autoscaling
* production-style orchestration concepts

---

# 🚀 Future Improvements

Planned reliability and production serving improvements:

* [✅] retry handling
* [✅] circuit breakers
* [✅] graceful degradation
* [✅] request shedding
* [✅] Redis failure handling
* [✅] autoscaler stabilization
* [✅] manual model training before deploy
* [✅] model artifact loading
* [✅] model metadata endpoint
* [✅] model-serving dashboard
* [ ] distributed scaling
* [ ] Redis HA / Sentinel / Cluster
* [ ] KEDA-based autoscaling
* [ ] model canary deployment
* [ ] model rollback workflow
* [ ] Triton Inference Server exploration
* [ ] vLLM serving concepts
* [ ] KServe / Ray Serve exploration

---

# 🚀 Learning Goals

This project focuses on:

* AI infrastructure engineering
* inference platform design
* distributed systems
* observability
* production operations
* autoscaling systems
* queue orchestration
* workload fairness
* infrastructure debugging
* Kubernetes reliability
* model-serving lifecycle
* training/serving separation

---

# 🚀 Repository Structure

```text
app/
├── api/
├── inference/
│   ├── autoscaler.py
│   ├── batch.py
│   ├── features.py
│   ├── metrics.py
│   ├── model.py
│   ├── queue_service.py
│   ├── scheduler.py
│   └── worker.py
│
scripts/
└── train_model.py

models/
└── anomaly-detector/
    └── v1/
        ├── model.pkl
        └── metadata.json

dashboards/
├── model-inference-overview.json
└── other-dashboard-json-files

k8s/
├── app-deployment.yaml
├── app-service.yaml
├── redis-deployment.yaml
├── redis-service.yaml
├── vip-worker-deployment.yaml
├── shared-worker-deployment.yaml
├── prometheus-configmap.yaml
├── prometheus-deployment.yaml
├── grafana-deployment.yaml
└── hpa.yaml

nginx.conf
prometheus.yaml
docker-compose.yaml
README.md
```

---
## Dynamic Batching 
The inference platform combines batching at two different layers.

### Application-level batching
The worker maintains its own batching mechanism to implement platform-specific traffic policies:

- VIP vs Free-tier scheduling 
- QoS enforcement
- Configurable batch size and wait time per tier 
- Fairness and admission control

This layer determines **which requests should be served together**.

### Triton Dynamic Batching 
Triton performs a second layer of batching immediately before model execution.
Its responsibility is to optimize serving efficiency by:

- Combine concurrent inference requests
- Reducing model execution overhead
- Increasing execution throughput
- Improving hardware utilization

This layer determines **how requests are executed efficiently**.

### Experimental Results

Compared with the non-batching baselines:

- Triton queue ration reduces by approximately **30%**
- Backend model executions reduces by approximately **3x**
- Request throughput decreased only slightly (~32 req/s)
- Average request and compute latencies increased slightly due to batching window

The results demonstrate the expected trade-off: dynamic batching significantly improves serving efficiency by reducing execution
overhead while introducing only a small increase in latency. 

## Inference-Aware Autoscaling Strategy

Scale workers when:
- Redis queue depth grows
- Worker processing latency increases
- Worker CPU is saturated
- Triton latency remains healthy

Scale Triton when:
- Triton queue latency increases
- Triton request latency increases
- Triton CPU/GPU is saturated
- Worker queue is not the main bottleneck

Do not scale blindly when:
- CPU is high but latency and queue depth are healthy
- Model execution latency is high but queue latency is low
- Dynamic batching improves execution count but worsens request latency too much


# 🚀 Author

Built as part of an AI Infrastructure Engineer transition roadmap focused on production AI serving systems, observability, autoscaling, Kubernetes reliability, and distributed inference infrastructure.
