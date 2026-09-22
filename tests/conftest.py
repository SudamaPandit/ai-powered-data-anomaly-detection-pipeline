from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from anomaly_pipeline.config import PipelineConfig, load_config
from anomaly_pipeline.domain import MetricSnapshot


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def pipeline_config(project_root: Path) -> PipelineConfig:
    return load_config(project_root / "config" / "claims.yml")


@pytest.fixture
def valid_claims() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "claim_id": ["C1", "C2", "C3"],
            "member_id": ["M1", "M2", "M3"],
            "provider_id": ["P1", "P2", "P3"],
            "service_date": ["2026-09-21"] * 3,
            "diagnosis_code": ["I10", "E11.9", "I10"],
            "claim_amount": [100.0, 200.0, 300.0],
            "claim_status": ["APPROVED", "PENDING", "DENIED"],
            "source_system": ["test"] * 3,
            "ingested_at": [
                "2026-09-22T09:00:00Z",
                "2026-09-22T09:15:00Z",
                "2026-09-22T09:30:00Z",
            ],
        }
    )


@pytest.fixture
def normal_history(pipeline_config: PipelineConfig) -> pd.DataFrame:
    rows = []
    for index in range(30):
        rows.append(
            {
                "row_count": 1_000 + (index % 7) - 3,
                "duplicate_rate": 0.002 + (index % 3) * 0.001,
                "null_member_rate": 0.004 + (index % 4) * 0.001,
                "invalid_amount_rate": 0.001,
                "invalid_status_rate": 0.001,
                "invalid_timestamp_rate": 0.001,
                "mean_amount": 250.0 + (index % 5),
                "p95_amount": 700.0 + (index % 6),
                "freshness_hours": 1.0 + (index % 4) * 0.1,
            }
        )
    return pd.DataFrame(rows, columns=list(pipeline_config.model.features))


@pytest.fixture
def normal_snapshot() -> MetricSnapshot:
    return MetricSnapshot(
        dataset="healthcare_claims_feed",
        batch_id="batch-1",
        observed_at=datetime(2026, 9, 22, 10, tzinfo=UTC),
        row_count=1_000,
        duplicate_rate=0.001,
        null_member_rate=0.002,
        invalid_amount_rate=0.0,
        invalid_status_rate=0.0,
        invalid_timestamp_rate=0.0,
        mean_amount=250.0,
        p95_amount=700.0,
        freshness_hours=1.0,
    )
