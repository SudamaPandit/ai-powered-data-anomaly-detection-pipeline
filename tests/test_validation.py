from __future__ import annotations

import pandas as pd
import pytest

from anomaly_pipeline.config import PipelineConfig
from anomaly_pipeline.validation import SchemaValidationError, prepare_claims


def test_prepares_types_and_normalizes_strings(
    valid_claims: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    valid_claims.loc[0, "claim_status"] = " APPROVED "
    valid_claims["claim_amount"] = valid_claims["claim_amount"].astype(object)
    valid_claims.loc[0, "claim_amount"] = "125.50"
    result = prepare_claims(valid_claims, pipeline_config.dataset)
    assert result.loc[0, "claim_status"] == "APPROVED"
    assert result.loc[0, "claim_amount"] == 125.5
    assert str(result["ingested_at"].dtype) == "datetime64[ns, UTC]"


def test_keeps_bad_values_as_null_for_profiling(
    valid_claims: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    valid_claims["claim_amount"] = valid_claims["claim_amount"].astype(object)
    valid_claims.loc[0, "claim_amount"] = "not-money"
    valid_claims.loc[1, "ingested_at"] = "not-a-time"
    result = prepare_claims(valid_claims, pipeline_config.dataset)
    assert pd.isna(result.loc[0, "claim_amount"])
    assert pd.isna(result.loc[1, "ingested_at"])


def test_rejects_missing_columns(
    valid_claims: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    with pytest.raises(SchemaValidationError, match="claim_id"):
        prepare_claims(valid_claims.drop(columns="claim_id"), pipeline_config.dataset)


def test_rejects_empty_batch(pipeline_config: PipelineConfig) -> None:
    empty = pd.DataFrame(columns=pipeline_config.dataset.required_columns)
    with pytest.raises(SchemaValidationError, match="empty"):
        prepare_claims(empty, pipeline_config.dataset)
