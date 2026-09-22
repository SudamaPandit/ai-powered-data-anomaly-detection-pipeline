from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from anomaly_pipeline.config import PipelineConfig
from anomaly_pipeline.detection.model import train_model
from anomaly_pipeline.domain import DetectionResult
from anomaly_pipeline.pipeline import file_batch_id, run_detection
from anomaly_pipeline.storage.sqlite_store import SQLiteAnomalyStore


def test_file_batch_id_is_content_based(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("same", encoding="utf-8")
    second.write_text("same", encoding="utf-8")
    assert file_batch_id(first) == file_batch_id(second)
    second.write_text("different", encoding="utf-8")
    assert file_batch_id(first) != file_batch_id(second)


def test_runs_pipeline_end_to_end(
    tmp_path: Path,
    valid_claims: pd.DataFrame,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    input_path = tmp_path / "claims.csv"
    valid_claims.to_csv(input_path, index=False)
    store = SQLiteAnomalyStore(tmp_path / "audit.db")
    alerts: list[DetectionResult] = []
    result = run_detection(
        input_path,
        normal_history,
        pipeline_config,
        train_model(normal_history, pipeline_config.model),
        store,
        observed_at=datetime(2026, 9, 22, 10, tzinfo=UTC),
        alert=alerts.append,
    )
    assert result.snapshot.row_count == 3
    assert result.is_anomaly
    assert store.count_runs() == 1
    assert alerts == [result]


def test_pipeline_run_is_idempotent(
    tmp_path: Path,
    valid_claims: pd.DataFrame,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    input_path = tmp_path / "claims.csv"
    valid_claims.to_csv(input_path, index=False)
    store = SQLiteAnomalyStore(tmp_path / "audit.db")
    model = train_model(normal_history, pipeline_config.model)
    first = run_detection(input_path, normal_history, pipeline_config, model, store)
    second = run_detection(input_path, normal_history, pipeline_config, model, store)
    assert first.run_id == second.run_id
    assert store.count_runs() == 1


def test_pipeline_rejects_missing_input(
    tmp_path: Path,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    store = SQLiteAnomalyStore(tmp_path / "audit.db")
    model = train_model(normal_history, pipeline_config.model)
    with pytest.raises(FileNotFoundError, match="not found"):
        run_detection(tmp_path / "missing.csv", normal_history, pipeline_config, model, store)
