from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    """Ordered severity used for alert routing."""

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_name(cls, value: str) -> Severity:
        try:
            return cls[value.upper()]
        except KeyError as exc:
            raise ValueError(f"Unsupported severity: {value}") from exc


@dataclass(frozen=True)
class MetricSnapshot:
    dataset: str
    batch_id: str
    observed_at: datetime
    row_count: int
    duplicate_rate: float
    null_member_rate: float
    invalid_amount_rate: float
    invalid_status_rate: float
    invalid_timestamp_rate: float
    mean_amount: float
    p95_amount: float
    freshness_hours: float

    def feature_dict(self) -> dict[str, float]:
        return {
            "row_count": float(self.row_count),
            "duplicate_rate": self.duplicate_rate,
            "null_member_rate": self.null_member_rate,
            "invalid_amount_rate": self.invalid_amount_rate,
            "invalid_status_rate": self.invalid_status_rate,
            "invalid_timestamp_rate": self.invalid_timestamp_rate,
            "mean_amount": self.mean_amount,
            "p95_amount": self.p95_amount,
            "freshness_hours": self.freshness_hours,
        }

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["observed_at"] = self.observed_at.astimezone(UTC).isoformat()
        return record


@dataclass(frozen=True)
class RuleFinding:
    rule_id: str
    severity: Severity
    metric: str
    observed: float
    threshold: float
    message: str

    def as_record(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "severity": self.severity.name,
        }


@dataclass(frozen=True)
class DetectionResult:
    run_id: str
    snapshot: MetricSnapshot
    model_score: float
    model_anomaly: bool
    final_severity: Severity
    findings: tuple[RuleFinding, ...] = field(default_factory=tuple)

    @property
    def is_anomaly(self) -> bool:
        return self.model_anomaly or bool(self.findings)

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            **self.snapshot.as_record(),
            "model_score": self.model_score,
            "model_anomaly": self.model_anomaly,
            "is_anomaly": self.is_anomaly,
            "final_severity": self.final_severity.name,
        }
