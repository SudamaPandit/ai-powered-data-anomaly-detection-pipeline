from __future__ import annotations

import pytest

from anomaly_pipeline.detection.scoring import final_severity
from anomaly_pipeline.domain import RuleFinding, Severity


def finding(severity: Severity) -> RuleFinding:
    return RuleFinding("test", severity, "metric", 1.0, 0.5, "test")


@pytest.mark.parametrize(
    ("findings", "model_anomaly", "expected"),
    [
        ((), False, Severity.INFO),
        ((finding(Severity.HIGH),), False, Severity.HIGH),
        ((), True, Severity.MEDIUM),
        ((finding(Severity.MEDIUM),), True, Severity.HIGH),
        ((finding(Severity.HIGH),), True, Severity.CRITICAL),
    ],
)
def test_final_severity(
    findings: tuple[RuleFinding, ...], model_anomaly: bool, expected: Severity
) -> None:
    assert final_severity(findings, model_anomaly) is expected
