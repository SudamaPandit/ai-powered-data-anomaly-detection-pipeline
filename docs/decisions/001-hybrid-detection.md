# ADR 001: Combine deterministic rules with unsupervised detection

Status: Accepted

## Context

Operational data anomalies fall into two groups. Some are explicit contract violations, such as negative amounts or duplicate business keys. Others are unusual combinations of individually plausible metrics. A single technique does not handle both groups well.

## Decision

Use configuration-driven rules for known controls and an Isolation Forest for multivariate batch behavior. Evaluate both independently and combine them through a small deterministic severity policy.

## Consequences

- Every known contract failure has a human-readable reason and threshold.
- The model can add evidence but cannot override a critical rule.
- Model training needs a representative history of normal metric snapshots.
- Thresholds and contamination must be tuned from operational outcomes.
- Alert review remains necessary because unsupervised output is not a diagnosis.

