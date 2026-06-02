# Anomaly Inference System

Production-style AI inference infrastructure project focused on queue-based inference, adaptive batching, QoS scheduling, autoscaling, and observability.

---

# 🚀 Overview

This project simulates a production AI inference platform with:

* Multi-tenant request isolation
* VIP vs Free-tier scheduling
* Queue-based asynchronous inference
* Adaptive batching
* Elastic worker orchestration
* Autoscaling control loops
* Full observability stack
* Infrastructure saturation analysis

The system was built as part of an AI Infrastructure Engineer transition roadmap focused on distributed systems, ML serving infrastructure, and inference platform engineering.

---

# 🏗️ System Architecture

```text
Client
   │
   ▼
Nginx Ingress
   │
   ▼
FastAPI App Instances
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
 ┌───────────────┐
 │ VIP Workers   │
 │ Shared Workers│
 └───────────────┘
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

cadvisor
nginx-exporter
worker metrics
application metrics
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
| `/metrics`         | Prometheus metrics              |

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

---

# 🚀 Autoscaling

The autoscaler dynamically adjusts:

* active VIP workers
* active shared workers

Based on:

* queue depth
* scaling thresholds
* cooldown intervals

Features:

* cooldown protection
* worker activation state
* elastic worker coordination
* scaling observability

---

# 🚀 Observability Stack

## Prometheus

Metrics collection across:

* FastAPI apps
* workers
* autoscaler
* nginx
* cadvisor

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

### Batching

* current batch size
* batch timeout

### Autoscaling

* scaling events
* worker elasticity

### Infrastructure

* CPU usage
* memory usage
* container count
* nginx metrics

---

# 🚀 Infrastructure Components

| Component      | Purpose                          |
| -------------- | -------------------------------- |
| FastAPI        | inference API                    |
| Redis          | queue + coordination             |
| Nginx          | ingress + load balancing         |
| Prometheus     | metrics collection               |
| Grafana        | observability dashboards         |
| cadvisor       | container infrastructure metrics |
| nginx-exporter | nginx Prometheus exporter        |

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
* observability-driven debugging

---

# 🚀 Running The System

## Start Infrastructure

```bash
docker compose up --build
```

---

# 🚀 Access Services

| Service    | URL                                            |
| ---------- | ---------------------------------------------- |
| FastAPI    | [http://localhost:8000](http://localhost:8000) |
| Prometheus | [http://localhost:9090](http://localhost:9090) |
| Grafana    | [http://localhost:3000](http://localhost:3000) |
| cadvisor   | [http://localhost:8080](http://localhost:8080) |

---

# 🚀 Example Load Testing

Burst-based load testing was used to simulate:

* queue pressure
* saturation
* autoscaling events
* latency degradation

The project explores:

* worker oversubscription
* infrastructure bottlenecks
* throughput plateaus
* queue growth behavior

---

# 🚀 Kubernetes Deployment

The system now supports Kubernetes-based deployment for production-style orchestration and workload management.

## Kubernetes Concepts Explored

* Deployments
* Replica orchestration
* Kubernetes Services
* EndpointSlice service discovery
* Self-healing infrastructure
* Declarative scaling
* Pod lifecycle management

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
 ┌───────────────────────┐
 │ anomaly-inference-pod │
 │ anomaly-inference-pod │
 │ anomaly-inference-pod │
 └───────────────────────┘
   │
   ▼
Redis Queue Layer
```

---

# 🚀 Kubernetes Deployment Features

The Kubernetes deployment supports:

* multi-pod inference serving
* service-level load balancing
* automatic pod recovery
* declarative replica scaling
* EndpointSlice-based service discovery

---

# 🚀 Kubernetes Manifests

| Manifest                  | Purpose            |
|---------------------------| ------------------ |
| `k8s/app-deployment.yaml` | FastAPI deployment |
| `k8s/app-service.yaml`    | Kubernetes Service |

---

# 🚀 Example Kubernetes Commands

## Deploy Application

```bash
kubectl apply -f k8s/app-deployment.yaml
kubectl apply -f k8s/app-service.yaml
```

## Verify Resources

```bash
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get endpointslices
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

# 🚀 Kubernetes Learning Outcomes

This phase explored:

* distributed workload orchestration
* control-plane reconciliation
* service discovery
* declarative infrastructure management
* containerized deployment workflows
* self-healing systems
* production-style orchestration concepts


# 🚀 Future Improvements

Planned reliability engineering features:

* [✅]  retry handling
* [✅] circuit breakers
* [✅] graceful degradation
* [✅]  request shedding
* [✅] Redis failure handling
* [✅] autoscaler stabilization
* distributed scaling

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

---

# 🚀 Repository Structure

```text
app/
├── api/
├── model/
│   ├── autoscaler.py
│   ├── batch.py
│   ├── metrics.py
│   ├── queue_service.py
│   ├── scheduler.py
│   ├── worker.py
│   └── model.py
│
├── dashboards/
├── nginx.conf
├── prometheus.yaml
├── docker-compose.yaml
└── README.md
```

---

# 🚀 Author

Built as part of an AI Infrastructure Engineer transition roadmap focused on production AI serving systems, observability, autoscaling, and distributed inference infrastructure.
