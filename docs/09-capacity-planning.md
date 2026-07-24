
# Capacity Planning

Capacity planning estimates how much serving infrastructure is required to safely handle expected traffic while meeting latency, reliability, and QoS goals.

For this project, capacity is planned across three main serving layers:

```text
API / Queue Admission
        ↓
VIP Worker / Shared Worker
        ↓
Triton Inference Server
        ↓
Model Execution
```

The goal is not to maximize throughput at any cost. The goal is to find the highest sustainable traffic level where the system remains stable, latency stays within target, and enough headroom remains for spikes, retries, model rollout overhead, and dependency variance.

These capacity numbers are based on local Kubernetes load testing and should be treated as benchmark estimates, not production guarantees.

---

## Maximum Capacity vs Safe Capacity

Maximum capacity is the highest throughput observed before the system becomes unstable.

Safe capacity is the highest sustained throughput where:

* queue depth remains stable
* backlog growth rate stays near zero
* P95/P99 latency stays within target
* error rate remains low
* load shedding is zero or minimal
* worker and Triton replicas still have headroom

Production systems should be sized based on safe capacity, not maximum capacity.

```text
Maximum capacity:
The highest throughput observed before the system starts breaking down.

Safe capacity:
The highest throughput the system can sustain while still meeting latency,
error-rate, queue-depth, and headroom targets.
```

In this project, safe capacity is more important than maximum capacity because the platform is designed for production-style inference serving, where predictable latency and reliability matter more than short-lived peak throughput.

---

## Basic Replica Sizing Formulas

```text
required_replicas = target_request_rate / safe_request_rate_per_replica
```

With headroom:

```text
required_capacity = target_request_rate / target_utilization
```

For example:

```text
If target traffic is 100 req/s
and target running utilization is 70%:

required_capacity = 100 / 0.7 = 143 req/s

If one shared worker safely handles 50 req/s:

required_shared_worker_replicas = 143 / 50 = ~3 workers
```

This means the system should not run workers at 100% of their observed maximum throughput. Running at around 70% utilization leaves room for traffic spikes, queue variance, retries, autoscaling delay, and model rollout overhead.

---

## VIP Worker / Shared Worker / Triton Capacity Planning

The system separates VIP and Free-tier traffic because they have different latency and QoS expectations.

```text
VIP traffic:
- lower latency target
- smaller batches
- shorter wait time
- more protected capacity

Free/shared traffic:
- higher throughput target
- larger batches
- more queue tolerance
- can be shed earlier under overload
```

---

### VIP Worker Capacity

Target traffic:

```text
50 req/s
```

Target running utilization:

```text
70%
```

Required capacity:

```text
50 / 0.7 = ~72 req/s
```

Current configuration:

```text
VIP worker replicas: 
- min replicas: 2
- max replicas: 3
```

Estimated required capacity per VIP worker:

```text
72 req/s / 3 replicas = ~24 req/s per VIP worker
```

The VIP worker pool is intentionally provisioned with fixed capacity because VIP traffic is latency-sensitive. The goal is to avoid waiting for autoscaling before VIP requests receive sufficient processing capacity.

Since VIP traffic is approximately one-third of Free-tier traffic, three VIP replicas provide enough reserved capacity for this local benchmark target.

---

### Shared Worker Capacity

Target traffic:

```text
80 req/s
```

Target running utilization:

```text
70%
```

Required capacity:

```text
80 / 0.7 = ~114 req/s
```

Current configuration:

```text
Shared worker replicas:
- min replicas: 2
- max replicas: 3
```

Autoscaling thresholds:

```text
worker processing latency P95: 900ms
CPU utilization: 70%
```

Estimated required capacity per shared worker at max replicas:

```text
114 req/s / 3 replicas = ~38 req/s per shared worker
```

The shared worker pool uses autoscaling because Free-tier traffic is more elastic and can tolerate more queueing than VIP traffic.

When Free-tier demand increases, shared workers should scale before load shedding begins. Load shedding should only happen when queue depth, queue wait latency, or backlog growth indicates that autoscaling is not recovering quickly enough.

---

### Triton Capacity

Target traffic:

```text
130 req/s
```

Target running utilization:

```text
70%
```

Required capacity:

```text
130 / 0.7 = ~186 req/s
```

Current configuration:

```text
Triton replicas:
- min replicas: 2
- max replicas: 4
```

Autoscaling thresholds:

```text
average Triton queue latency: 200ms
average Triton request latency: 500ms
CPU utilization: 70%
```

Estimated required capacity per Triton replica at minimum replicas:

```text
186 req/s / 2 replicas = ~93 req/s per Triton replica
```

Estimated required capacity per Triton replica at maximum replicas:

```text
186 req/s / 4 replicas = ~46 req/s per Triton replica
```

Triton capacity should be scaled when model-server latency or queue latency rises. Adding more workers does not help if Triton is already the bottleneck.

Worker adaptive batching must also stay compatible with Triton model configuration:

```text
worker max_batch_size <= Triton max_batch_size
```

Large worker batches can improve throughput, but they can also increase worker end-to-end latency and queue wait time. For this reason, Triton `max_batch_size`, worker `max_batch_size`, and worker `max_wait_time` should be tuned together.

---

## Load Test Results

The following table summarizes local Kubernetes benchmark results.

| Test                                | Shared Workers | VIP Workers | Triton Replicas | Offered Load |                              Processed Rate | Queue Trend                       |                Worker P95 |      Load Shedding | Verdict    | Load Test Batch Size / Wave |
|-------------------------------------|---------------:|------------:|----------------:|-------------:|--------------------------------------------:|-----------------------------------|--------------------------:|-------------------:|------------|----------------------------:|
| Baseline                            |              2 |           2 |               3 |     45 req/s |   ~45 req/s (FREE: 31 req/s, VIP: 14 req/s) | Stable                            | Shared: 230ms, VIP: 225ms |                  0 | Safe       |                         100 |
| Medium load                         |              2 |           2 |               3 |    115 req/s |  ~115 req/s (FREE: 80 req/s, VIP: 35 req/s) | Stable                            | Shared: 458ms, VIP: 440ms |                  0 | Safe       |                         300 |
| High load                           |              2 |           2 |               3 |    160 req/s | ~150 req/s (FREE: 105 req/s, VIP: 45 req/s) | Free: growing, VIP: Slight growth |  Shared: 2.4s, VIP: 485ms | Free: Some, VIP: 0 | Overloaded |                         500 |
| High load with autoscaling occurred |              3 |           3 |               4 |    160 req/s | ~160 req/s (FREE: 115 req/s, VIP: 45 req/s) | Stable / slower growth            | Shared: 850ms, VIP: 600ms |                Low | Improved   |                         700 |

---

## Load Test Interpretation

The baseline test shows that the system is healthy at low traffic. Processed throughput matches offered load, queue depth remains stable, worker P95 latency remains low, and no load shedding occurs.

At 115 req/s, the system remains within the safe operating range. Processed throughput matches offered load, both Free and VIP queues remain stable, and no load shedding occurs. This is the strongest current safe-capacity data point.

At 160 req/s with 2 shared workers, 2 VIP workers, and 3 Triton replicas, the system becomes overloaded. Processed throughput falls behind offered load, Free queue depth grows, VIP queue depth shows slight growth, and Free-tier load shedding begins. This indicates that the shared worker path is the first layer to exceed its safe operating envelope.

After autoscaling increases the system to 3 shared workers, 3 VIP workers, and 4 Triton replicas, the system processes approximately 160 req/s and queue growth slows. Shared-worker P95 improves to around 850ms, which is below the 900ms threshold but close to the limit. VIP P95 reaches around 600ms, which is at the VIP autoscaling threshold.

This result shows that autoscaling improves the overloaded scenario, but the system is near its safe capacity boundary. Further increases in traffic would likely require additional tuning of worker batching, Triton dynamic batching, autoscaling thresholds, or max replica limits.

---

## Capacity Conclusion

Based on these local tests, the estimated operating ranges are:

```text
Safe:
~45 req/s with 2 shared workers, 2 VIP workers, and 3 Triton replicas

Validated safe range:
~115 req/s with 2 shared workers, 2 VIP workers, and 3 Triton replicas

Overloaded:
~160 req/s before autoscaling, with Free queue growth and Free-tier load shedding

Improved but near capacity boundary:
~160 req/s after autoscaling to 3 shared workers, 3 VIP workers, and 4 Triton replicas
```

For this local Kubernetes setup, a reasonable documented safe capacity estimate is:

```text
Approximately 115 req/s under the stable tested configuration.
```

A higher operating point of approximately 160 req/s is possible after autoscaling, but it should be treated as near the capacity boundary because worker P95 latency approaches the configured thresholds and load shedding remains non-zero.

These numbers are local benchmark estimates, not production SLAs.

---

## Bottleneck Interpretation

| Signal                                  | Meaning                                          | Capacity Action                                                                |
| --------------------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------ |
| Queue depth rising                      | Workers cannot drain queue fast enough           | Add workers, reduce batch wait, or tune batch size                             |
| Queue wait P95 rising                   | Jobs are waiting too long before processing      | Scale workers or shed lower-priority traffic                                   |
| Worker P95 rising + Triton latency low  | Worker-side bottleneck                           | Optimize worker logic, Redis access, serialization, batching, or result saving |
| Worker P95 rising + Triton latency high | Triton/model serving bottleneck                  | Add Triton replicas or tune Triton dynamic batching                            |
| Triton queue latency rising             | Triton is saturated or batching wait is too high | Add Triton replicas or reduce Triton max queue delay                           |
| Load shedding starts                    | Demand exceeds safe capacity                     | Scale, reject Free traffic, protect VIP                                        |
| HPA desired > available                 | Kubernetes cannot satisfy scaling target         | Check scheduling, resource requests, limits, or node capacity                  |
| Replicas high + low traffic             | Over-provisioning                                | Reduce min replicas or adjust autoscaling thresholds                           |
| Processed rate below ingress rate       | System cannot keep up with incoming demand       | Scale bottlenecked layer or shed load                                          |
| Effective batch size too low            | Batching is not being used efficiently           | Increase traffic, adjust preferred batch sizes, or tune wait time              |
| Effective batch size high + P95 high    | Batching improves throughput but hurts latency   | Reduce max batch size or max wait time                                         |

---

## Autoscaling vs Load Shedding

Autoscaling should trigger before load shedding.

Load shedding should only happen when queue depth, queue wait latency, or backlog growth shows that the system is no longer recovering quickly enough.

```text
Autoscaling:
Adds capacity when demand increases.

Load shedding:
Rejects work when the system is outside its safe operating envelope.
```

The system should not rely on autoscaling alone because autoscaling takes time. During sudden bursts, queue depth can grow faster than new replicas become ready.

For this reason, the platform uses both strategies:

```text
1. Autoscaling increases worker or Triton capacity.
2. Load shedding protects the system when capacity cannot catch up.
3. QoS rules protect VIP traffic before Free-tier traffic.
```

---

## Load Shedding Strategy

Free-tier traffic should be shed before VIP traffic.

Example load shedding conditions:

```text
Shed Free traffic when:
- Free queue depth exceeds the configured max load
- Free backlog growth remains positive
- Shared workers are near max replicas
- Free queue wait P95 exceeds target

Shed VIP traffic only when:
- VIP queue depth exceeds its safe limit
- VIP queue wait P95 exceeds target
- VIP workers are already saturated
- critical dependencies are unavailable
```

Dependency failures should return service-unavailable errors instead of normal load-shedding responses.

```text
QueueFullError:
Return 429 Too Many Requests

RedisUnavailableError:
Return 503 Service Unavailable
```

This distinction matters because queue-full means the system is intentionally rejecting work to preserve stability, while Redis unavailable means a critical dependency has failed.

---

## Autoscaling Threshold Strategy

### Shared Worker Autoscaling

Scale shared workers when:

```text
- shared-worker processing P95 approaches 800ms
- Free queue depth exceeds 450
- Free backlog growth rate remains positive
- CPU utilization approaches 70%
```

Shared workers should scale before Free-tier load shedding begins.

---

### VIP Worker Autoscaling

Scale shared workers when:

```text
- shared-worker processing P95 approaches 600ms
- Free queue depth exceeds 150
- Free backlog growth rate remains positive
- CPU utilization approaches 70%
```

---

### Triton Autoscaling

Scale Triton when:

```text
- average Triton queue latency approaches 200ms
- average Triton request latency approaches 500ms
- requests per Triton replica increases
- Triton CPU utilization approaches 70%
```

Triton should be scaled when model-server latency rises. Adding more workers will not solve a Triton bottleneck if Triton is already saturated.

---

## Worker Batching and Triton Batching

This system has two batching layers:

```text
Redis queue
   ↓
Worker adaptive batching
   ↓
Triton dynamic batching
   ↓
Model execution
```

Worker batching controls how many jobs a worker pulls from Redis before sending inference requests.

Triton dynamic batching controls how Triton combines inference requests for model execution.

Increasing worker batch size and worker max wait time can improve throughput, but it can also increase:

```text
- queue wait latency
- worker end-to-end processing latency
- head-of-line blocking
- tail latency for VIP traffic
```

The worker batch size must not exceed the Triton model's configured `max_batch_size`.

```text
worker max_batch_size <= Triton max_batch_size
```

For QoS, VIP workers should generally use smaller batches and shorter wait times, while shared workers can use larger batches to improve throughput.

---

## Known Limitations

These results are based on local Kubernetes testing, not a production cloud environment.

Current limitations:

```text
- local CPU-only environment
- no GPU capacity measurement
- no cAdvisor/kubelet container CPU and memory metrics yet
- Docker Desktop / local machine resource contention
- lightweight anomaly detection models
- synthetic load-test traffic
- limited test duration
```

In a production environment, this capacity planning process would be repeated with:

```text
- dedicated nodes
- realistic traffic distributions
- representative model sizes
- cloud or GPU resource metrics
- longer-duration load tests
- container-level CPU and memory metrics
- production autoscaling policies
```

The absolute throughput numbers are environment-specific, but the methodology is production-relevant.

## Capacity Planning Summary

Capacity planning for AI serving means estimating how much infrastructure is required to handle target traffic while meeting latency, reliability, and QoS goals.

I do not size the system based only on maximum observed throughput. I look for the safe operating envelope: the highest sustained load where processed throughput matches ingress, queue depth remains stable, P95/P99 latency stays within target, error rate remains low, and the system still has headroom.

In this project, I plan capacity separately for VIP workers, shared workers, and Triton because each layer can become the bottleneck independently. VIP traffic receives more protected capacity, while Free-tier traffic can tolerate more queueing and can be shed first under overload.

Autoscaling is used to add capacity, while load shedding protects the system when autoscaling cannot recover quickly enough. The goal is efficient, stable serving — not simply maximum throughput.
