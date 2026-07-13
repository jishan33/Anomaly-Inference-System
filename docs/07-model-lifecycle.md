# Model Registry and Artifact Management

The platform includes a lightweight model registry layer that tracks mode metadata separately from model serving.

Triton is responsible for executing model inference, while the model registry is responsible for describing which models exist, 
which versions are stable or candidate versions, and which aliases should be used by serving workloads.

This separation allows the platform to support safe model lifecycle operations such as promotion, rollback, canary deployment, 
and shadow validation without changing application code.

The registry tracks: 

- Model name
- Model owner
- Serving Backend
- Artifact path
- Model versions
- Model aliases
- Rollout eligibility
- Input contract 
- Output contract

Workers resolve logical aliases such as `stable`, `candidate`, `canary`, or `shadow` into physical Triton model versions 
before calling Triton.

This makes model routing safer and more production-like because serving code depends on stable logical aliases rather than
hardcoded model versions.

## Model Lifecycle States

```text
- registered
- shadow
- canary
- stable
- deprecated
- archived

ex: 
shadow = model receives copied production traffic but does not affect user response
canary = model receives a small percentage of real production traffic
stable = model is the default production version

```
### Lifecycle Flow Diagram

```text
                    New Model Artifact
                            │
                            ▼
                    Registered
                            │
                            ▼
                    Candidate
                            │
                            ├── Shadow Validation
                            │        │
                            │        ▼
                            │   Metrics Comparison
                            │
                            ▼
                    Canary Rollout
                            │
                            ▼
                    Stable Promotion
                            │
                            ▼
                    Deprecated / Archived
```

## Promotion Flow
```Text
shadow validation
   ↓
canary rollout
   ↓
stable promotion
```

## Promotion Criteria

A candidate model can be promoted only if:

| Signal | Requirement |
|---|---|
| Prediction disagreement | Within acceptable threshold |
| Score difference | No major drift from stable model |
| Latency | No meaningful regression |
| Error rate | No increase |
| Output contract | Compatible |
| Rollout eligibility | `rollout_eligible: true` |


## Rollback rules
```text
Rollback should happen if:

- canary error rate increases
- latency exceeds SLO
- prediction disagreement is unexpectedly high
- candidate model produces invalid outputs
- Triton serving errors increase
```

## Rollback Action
Rollback is performed by updating the runtime rollout configuration and redeploying the affected workloads.

If a canary or shadow rollout shows unsafe behavior, the platform can stop routing traffic to the candidate model by changing:

`MODEL_ROLLOUT_MODE: "stable"`

After updating the Kubernetes ConfigMap, apply the configuration and restart the relevant deployments:
```Text
kubectl apply -f k8s/
kubectl rollout restart deployment shared-worker
kubectl rollout restart deployment vip-worker
```
This returns inference traffic to the stable model version resolved by the model registry.

In the current architecture, rollback is controlled through rollout mode configuration rather than application code changes.

## Rollout Eligibility Enforcement

```Text

Before a worker routes traffic to a model version, the platform resolves the required alias or version through the model registry.

The selected version must be marked as `rollout_eligible: true` before it can receive inference traffic.

This prevents inactive, deprecated, experimental, or unsafe model versions from being served accidentally. 

```

## Governance boundary

```Text
Model Registry:
tracks model metadata, aliases, lifecycle state, artifact paths, and contract metadata 

Triton:
loads and execute model versions

Workers: 
resolves model name/version and calls Triton

Grafana/Prometheus:
validate model behaviour and rollout safety
```

