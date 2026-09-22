from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
import pytest

from anomaly_pipeline.config import PipelineConfig
from anomaly_pipeline.profiling import profile_batch
from anomaly_pipeline.validation import prepare_claims


def test_profiles_valid_batch(valid_claims: pd.DataFrame, pipeline_config: PipelineConfig) -> None:
    prepared = prepare_claims(valid_claims, pipeline_config.dataset)
    result = profile_batch(
        prepared,
        pipeline_config.dataset,
        batch_id="abc",
        observed_at=datetime(2026, 9, 22, 10, tzinfo=UTC),
    )
    assert result.row_count == 3
    assert result.duplicate_rate == 0
    assert result.mean_amount == 200
    assert result.p95_amount == pytest.approx(290)
    assert result.freshness_hours == 0.5


def test_profiles_known_bad_values(
    valid_claims: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    valid_claims.loc[1, "claim_id"] = "C1"
    valid_claims.loc[0, "member_id"] = " "
    valid_claims.loc[0, "claim_amount"] = -1
    valid_claims.loc[0, "claim_status"] = "OTHER"
    valid_claims.loc[0, "ingested_at"] = "bad"
    prepared = prepare_claims(valid_claims, pipeline_config.dataset)
    result = profile_batch(prepared, pipeline_config.dataset, batch_id="abc")
    assert result.duplicate_rate == pytest.approx(2 / 3)
    assert result.null_member_rate == pytest.approx(1 / 3)
    assert result.invalid_amount_rate == pytest.approx(1 / 3)
    assert result.invalid_status_rate == pytest.approx(1 / 3)
    assert result.invalid_timestamp_rate == pytest.approx(1 / 3)


def test_uses_sentinel_when_all_timestamps_invalid(
    valid_claims: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    valid_claims["ingested_at"] = "bad"
    prepared = prepare_claims(valid_claims, pipeline_config.dataset)
    result = profile_batch(prepared, pipeline_config.dataset, batch_id="abc")
    assert result.freshness_hours == 1_000_000


def test_rejects_empty_profile(pipeline_config: PipelineConfig) -> None:
    with pytest.raises(ValueError, match="empty"):
        profile_batch(pd.DataFrame(), pipeline_config.dataset, batch_id="abc")
