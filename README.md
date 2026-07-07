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
* [✅] distributed scaling
* [⚠️] Redis HA / Sentinel / Cluster
* [✅] KEDA-based autoscaling
* [✅] model canary deployment
* [✅] model rollback workflow
* [✅] Triton Inference Server exploration
* [⏳] vLLM serving concepts
* [⏳] KServe / Ray Serve exploration
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

## KEDA Multi-Signal Inference-Aware Autoscaling

This system uses separate autoscaling control loops for the worker and Triton deployments because they represent different stages of the inference pipeline and become bottlenecks under different conditions.

### Shared Worker Autoscaling

The shared worker deployment uses multiple autoscaling signals:

* Redis queue depth
* Worker processing latency
* CPU utilization

Each signal provides different information about the health of the worker tier.

**Redis queue depth** directly measures the backlog of unprocessed inference requests.

```text
Redis queue depth increases
        ↓
Workers cannot dequeue jobs fast enough
        ↓
Scale worker replicas
```

**Worker processing latency** indicates how long workers spend processing requests. An increase in processing latency suggests the worker tier is approaching saturation.

**CPU utilization** provides additional confirmation that workers are actively consuming compute resources and helps distinguish sustained resource pressure from temporary traffic bursts.

Using multiple signals provides a more robust scaling strategy than relying on a single metric. Queue depth reflects demand, processing latency reflects service performance, and CPU utilization reflects resource consumption.

### Triton Autoscaling

The Triton deployment also uses multiple inference-aware signals:

* Triton queue latency
* Triton request latency
* CPU utilization

**Triton queue latency** measures how long inference requests wait before execution. Increasing queue latency indicates that incoming requests are arriving faster than Triton can schedule them.

```text
Triton queue latency increases
        ↓
Inference server becomes saturated
        ↓
Scale Triton replicas
```

**Triton request latency** measures end-to-end request processing within Triton and helps identify degradation in overall serving performance.

**CPU utilization** indicates whether Triton's serving resources are becoming saturated and provides an additional scaling signal during sustained workloads.

### Trade-offs

The worker and Triton deployments are scaled independently because they serve different responsibilities within the inference pipeline.

Worker autoscaling increases the system's ability to dequeue, preprocess, and dispatch inference requests.

Triton autoscaling increases the system's model serving capacity.

Scaling only the worker tier can overload Triton if the inference server is already saturated. Conversely, scaling Triton alone may leave additional inference capacity underutilized if workers cannot dispatch requests quickly enough.

A production AI inference platform should identify where latency is accumulating and scale the constrained stage of the pipeline rather than applying uniform scaling across all components. This inference-aware strategy improves resource utilization while maintaining predictable latency under varying workloads.

## Model Versioning & Output Contract

The inference platform supports serving multiple model versions simultaneously using Triton Inference Server.

```text
anomaly_detector
├── 1/
│   └── model.py
├── 2/
│   └── model.py
└── config.pbtxt
```

The worker explicitly selects the Triton model version through the Triton client `model_version` parameter rather than relying on the default latest version. This allows multiple versions of the same model to coexist and enables safe production rollout strategies such as canary deployments and shadow traffic.

### Output Contract

Both Version 1 and Version 2 expose the same inference contract.

| Output | Description |
|---------|-------------|
| `OUTPUT` | Binary anomaly prediction (`0 = Normal`, `1 = Anomaly`) |
| `SCORE` | IsolationForest anomaly score returned by `decision_function()` |

Example response:

```json
{
    "prediction": 1,
    "score": -0.42,
    "model_version": "1"
}
```

Maintaining a consistent output contract allows the worker to switch between model versions without requiring changes to downstream consumers.

### Versioning Strategy

The inference client explicitly selects the Triton model version through the `model_version` parameter.

This enables multiple versions of the model to coexist while preserving a stable client interface. 

### Production Rollout Strategy

Multiple model versions enable safer production deployments by reducing the blast radius of model updates.

Typical rollout strategies include:

- Explicit version selection
- Canary deployment
- Shadow traffic
- Fast rollback

For this project:

- Version 1 is the production inference path.
- Version 2 is executed as a shadow model for validation.
- The Version 1 result is stored and returned to clients.
- Version 2 predictions and anomaly scores are logged for comparison without impacting production responses.

This approach allows new model versions to be evaluated under real production traffic while preserving the stability of the production inference service.

## Canary Deployment

The inference platform supports configurable canary deployment to safely validate new model versions under real production traffic while minimizing the blast radius of potential regressions.

### Architecture

```text
                    Worker

                       │
                       ▼
         MODEL_VERSION_2_CANARY_PERCENTAGE
                       │
          ┌────────────┴────────────┐
          │                         │
     95% Traffic               5% Traffic
          │                         │
          ▼                         ▼
Model Version 1             Model Version 2
          │                         │
          └────────────┬────────────┘
                       ▼
                Triton Inference Server
```

The worker determines which model version to invoke using the configurable canary percentage stored in the Kubernetes ConfigMap.

```yaml
MODEL_VERSION_2_CANARY_PERCENTAGE: "0.05"
```

This separates rollout policy from application logic, allowing traffic distribution to be adjusted without modifying the inference code.

### Observability

The canary deployment is monitored using version-specific inference metrics, including:

* Request rate by model version
* Triton average request latency
* Triton queue latency
* Triton inference latency
* Effective batch size
* Inference execution count

During load testing, approximately **5%** of requests were routed to **Model Version 2**, confirming that the routing policy operated as expected.

Version 2 exhibited a slightly higher average inference latency than Version 1. This is likely due to reduced batching efficiency, as the lower canary traffic provides fewer opportunities for Triton's dynamic batching algorithm to form larger batches.

### Rollback Strategy

The rollout percentage is externally configured through the Kubernetes ConfigMap.

If the canary model exhibits degraded performance or unexpected behaviour, traffic can immediately be redirected back to the stable model by setting:

```yaml
MODEL_VERSION_2_CANARY_PERCENTAGE: "0.0"
```

and restarting the worker deployment.

This immediately routes **100%** of production traffic back to the stable model while leaving the new model deployed for further investigation.

If the issue originates from the application itself (for example, inference routing logic or worker implementation), the appropriate recovery mechanism is to roll back the Kubernetes Deployment to a previously known-good container image.

### Benefits

This canary deployment strategy provides several production advantages:

* Gradually validates new model versions using real production traffic.
* Reduces the blast radius of model regressions.
* Enables version-specific performance comparison before full promotion.
* Supports rapid rollback through configuration changes.
* Separates model rollout policy from application implementation.

By externalizing rollout configuration and combining it with version-aware observability, the platform can safely introduce new model versions while maintaining production reliability.


# 🚀 Author

Built as part of an AI Infrastructure Engineer transition roadmap focused on production AI serving systems, observability, autoscaling, Kubernetes reliability, and distributed inference infrastructure.
