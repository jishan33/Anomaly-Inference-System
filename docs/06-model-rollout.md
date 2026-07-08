# Model Rollout

## Overview

The platform supports production-style model deployment strategies.

Current rollout modes:

- Stable
- Canary
- Shadow

---

# Model Versioning

The Triton model repository supports multiple versions.

```text
Version 1

Stable

Version 2

Candidate
```

---

# Output Contract

Each model returns:

- Prediction
- Anomaly score

Maintaining a stable output schema ensures compatibility between model versions.

---

# Canary Deployment

Traffic is routed according to a configurable percentage.

```text
95%

↓

Version 1

5%

↓

Version 2
```

Version-specific metrics monitor rollout behaviour.

---

# Shadow Traffic

Both models execute.

```text
Request

↓

Version 1

↓

Return response

↓

Version 2

↓

Compare only
```

The candidate model never affects production responses.

---

# Model Comparison

The platform compares:

- Prediction agreement
- Prediction disagreement
- Score difference
- Prediction distribution
- Score distribution

---

# Promotion Criteria

Infrastructure:

- Latency
- Error rate
- Queue latency
- Resource utilization

Model Behaviour:

- Prediction agreement
- Prediction distribution
- Score distribution
- Output compatibility

---

# Rollback

Model rollback is performed by updating rollout configuration.

Application rollback is handled through Kubernetes deployment rollback.