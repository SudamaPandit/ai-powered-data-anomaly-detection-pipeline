from __future__ import annotations

from typing import Protocol

from anomaly_pipeline.domain import DetectionResult


class AnomalyStore(Protocol):
    def save(self, result: DetectionResult) -> None:
        """Persist a complete detection result idempotently."""
