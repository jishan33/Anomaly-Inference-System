
# Cost-Aware Inference Optimization

Cost-aware inference optimization focuses on meeting latency and reliability targets without over-provisioning serving infrastructure.

In this project, cost is represented through local infrastructure proxies such as worker replicas, 
Triton replicas, CPU utilization, queue depth, request throughput, and batching efficiency.

The platform should not blindly scale out whenever traffic increases. Instead scaling decisions should consider where 
the bottleneck is introduced: 

- API ingress
- Redis queue
- Worker processing 
- Triton queueing 
- Model execution 
- Downstream result storage

Adding replicas is useful only when it reduces the actual bottleneck. If latency is caused by Triton queueing, adding 
API replicas may not help. If latency is caused by worker backlog, increasing Triton capacity alone may not help.

The goal is to meet the required SLO with the smallest stable amount of serving capacity.

## Main Cost Levers in This System

The main cose levers in this platform include:
```Text
- Worker replica count
- Triton replica count
- Autoscaling thresholds
- Queue depth thresholds
- Batch size
- Dynamic batching 
- CPU/memory allocation
- VIP vs shared worker separation 
- Canary/Shadow traffic overhead
```
 
Shadow traffic improves validation safety, but it also increases inference compute because the candidate model runs 
in parallel with the stable model.


## Metrics to Use 

Cost-aware inference analysis should consider multiple signals together:

```Text 
- Request rate 
- Queue depth
- Worker processing latency
- Triton request latency
- Triton queue latency
- Batch size 
- Replica count 
- CPU utilization
- Memory utilization
- Error rate 
```

Example Interpretations: 

```Text
High replica count + low CPU utilization + low queue depth
= possible over-provisioning

High queue depth + high latency + high CPU/Triton latency
= under-provisioning or bottleneck

High Triton queue latency + low worker latency
= inference server bottleneck

High worker latency + low Triton latency
= worker-side bottleneck
```

## Cost-Efficiency Signals

Useful signals include: 
```Text
- requests per worker replica
- requests per Triton replica
- requests per CPU core
- average batch size 
- latency per replica
```

Example formulas: 
```Text
- requests_per_worker = total_request_rate / worker_replicas
- requests_per_triton_replica = triton_request_rate / triton_replicas
- cost_efficiency_proxy = successful_requests / total_replicas
```


## Latency vs Cost Trade-off
| Optimization | Benefit | Cost/Risk |
|---|---|---|
| More worker replicas | Lower queue delay | Higher compute cost |
| More Triton replicas | Higher inference capacity | Higher serving cost |
| Larger batch size | Better throughput | Higher latency |
| Dynamic batching | Better utilization | Queue wait time may increase |
| Lower autoscaling threshold | Faster scale-out | More over-provisioning |
| Higher autoscaling threshold | Lower cost | Higher risk of latency spikes |
| Shadow testing | Safer model validation | Extra inference compute |
| Separate VIP workers | Better QoS isolation | More reserved capacity |