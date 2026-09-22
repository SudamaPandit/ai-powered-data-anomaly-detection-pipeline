from __future__ import annotations

from anomaly_pipeline.domain import RuleFinding, Severity


def final_severity(findings: tuple[RuleFinding, ...], model_anomaly: bool) -> Severity:
    """Combine interpretable controls with the model without hiding rule failures."""
    rule_severity = max((finding.severity for finding in findings), default=Severity.INFO)
    if not model_anomaly:
        return rule_severity
    if rule_severity >= Severity.HIGH:
        return Severity.CRITICAL
    if rule_severity >= Severity.MEDIUM:
        return Severity.HIGH
    return Severity.MEDIUM
