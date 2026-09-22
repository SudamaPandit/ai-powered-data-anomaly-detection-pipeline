from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from anomaly_pipeline.config import RuleThreshold
from anomaly_pipeline.domain import MetricSnapshot, RuleFinding

DIRECT_METRICS = {
    "duplicate_rate": "duplicate_rate",
    "null_member_rate": "null_member_rate",
    "invalid_amount_rate": "invalid_amount_rate",
    "invalid_status_rate": "invalid_status_rate",
    "invalid_timestamp_rate": "invalid_timestamp_rate",
    "freshness_hours": "freshness_hours",
}


def _finding(
    rule_id: str,
    config: RuleThreshold,
    observed: float,
    message: str,
) -> RuleFinding:
    return RuleFinding(
        rule_id=rule_id,
        severity=config.severity,
        metric=rule_id,
        observed=observed,
        threshold=config.threshold,
        message=message,
    )


def evaluate_rules(
    snapshot: MetricSnapshot,
    history: pd.DataFrame,
    rules: dict[str, RuleThreshold],
) -> tuple[RuleFinding, ...]:
    """Evaluate deterministic controls before model output is considered."""
    findings: list[RuleFinding] = []
    for rule_id, attribute in DIRECT_METRICS.items():
        rule = rules.get(rule_id)
        if not rule or not rule.enabled:
            continue
        observed = float(getattr(snapshot, attribute))
        if observed > rule.threshold:
            findings.append(
                _finding(
                    rule_id,
                    rule,
                    observed,
                    f"{attribute} is {observed:.4f}, above the configured limit "
                    f"{rule.threshold:.4f}",
                )
            )

    volume_rule = rules.get("volume_drop_rate")
    if volume_rule and volume_rule.enabled and "row_count" in history:
        baseline = float(pd.to_numeric(history["row_count"], errors="coerce").median())
        if np.isfinite(baseline) and baseline > 0:
            drop_rate = max(0.0, (baseline - snapshot.row_count) / baseline)
            if drop_rate > volume_rule.threshold:
                findings.append(
                    _finding(
                        "volume_drop_rate",
                        volume_rule,
                        drop_rate,
                        f"batch volume dropped {drop_rate:.1%} from the historical median",
                    )
                )

    amount_rule = rules.get("mean_amount_shift_rate")
    if amount_rule and amount_rule.enabled and "mean_amount" in history:
        baseline = float(pd.to_numeric(history["mean_amount"], errors="coerce").median())
        if np.isfinite(baseline) and baseline > 0:
            shift_rate = abs(snapshot.mean_amount - baseline) / baseline
            if shift_rate > amount_rule.threshold:
                findings.append(
                    _finding(
                        "mean_amount_shift_rate",
                        amount_rule,
                        shift_rate,
                        f"mean claim amount shifted {shift_rate:.1%} from the historical median",
                    )
                )

    return tuple(sorted(findings, key=lambda item: item.severity, reverse=True))


def enabled_rule_ids(rules: dict[str, RuleThreshold]) -> Iterable[str]:
    return (rule_id for rule_id, rule in rules.items() if rule.enabled)
