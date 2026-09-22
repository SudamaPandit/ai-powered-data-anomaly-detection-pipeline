from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from anomaly_pipeline.domain import DetectionResult, MetricSnapshot, RuleFinding, Severity
from anomaly_pipeline.storage.bigquery_store import BigQueryAnomalyStore, BigQueryWriteError
from anomaly_pipeline.storage.sqlite_store import SQLiteAnomalyStore


def result(snapshot: MetricSnapshot, run_id: str = "run-1") -> DetectionResult:
    return DetectionResult(
        run_id=run_id,
        snapshot=snapshot,
        model_score=0.12,
        model_anomaly=True,
        final_severity=Severity.HIGH,
        findings=(
            RuleFinding("duplicate_rate", Severity.HIGH, "duplicate_rate", 0.2, 0.02, "bad"),
        ),
    )


def test_sqlite_store_persists_run_and_findings(
    tmp_path: Path, normal_snapshot: MetricSnapshot
) -> None:
    path = tmp_path / "audit.db"
    store = SQLiteAnomalyStore(path)
    store.save(result(normal_snapshot))
    assert store.count_runs() == 1
    with sqlite3.connect(path) as connection:
        finding_count = connection.execute("SELECT COUNT(*) FROM rule_findings").fetchone()[0]
    assert finding_count == 1


def test_sqlite_store_is_idempotent_by_dataset_and_batch(
    tmp_path: Path, normal_snapshot: MetricSnapshot
) -> None:
    store = SQLiteAnomalyStore(tmp_path / "audit.db")
    store.save(result(normal_snapshot, "run-1"))
    store.save(result(replace(normal_snapshot), "run-2"))
    assert store.count_runs() == 1


class FakeBigQueryClient:
    def __init__(self, *, project: str, errors: list[dict[str, object]] | None = None) -> None:
        self.project = project
        self.errors = errors or []
        self.calls: list[tuple[str, list[dict[str, object]]]] = []

    def insert_rows_json(
        self, table: str, rows: list[dict[str, object]], row_ids: list[str]
    ) -> list[dict[str, object]]:
        self.calls.append((table, rows))
        return self.errors


def test_bigquery_store_writes_both_tables(normal_snapshot: MetricSnapshot) -> None:
    client = FakeBigQueryClient(project="demo")
    store = BigQueryAnomalyStore("demo", "observability", client_factory=lambda **_: client)
    store.save(result(normal_snapshot))
    assert [call[0] for call in client.calls] == [
        "demo.observability.detection_runs",
        "demo.observability.rule_findings",
    ]


def test_bigquery_store_surfaces_write_errors(normal_snapshot: MetricSnapshot) -> None:
    client = FakeBigQueryClient(project="demo", errors=[{"reason": "invalid"}])
    store = BigQueryAnomalyStore("demo", "observability", client_factory=lambda **_: client)
    with pytest.raises(BigQueryWriteError, match="detection run"):
        store.save(result(normal_snapshot))
