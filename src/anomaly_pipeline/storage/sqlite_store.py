from __future__ import annotations

import sqlite3
from pathlib import Path

from anomaly_pipeline.domain import DetectionResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS detection_runs (
    run_id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    metrics_json TEXT NOT NULL,
    model_score REAL NOT NULL,
    model_anomaly INTEGER NOT NULL,
    is_anomaly INTEGER NOT NULL,
    final_severity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dataset, batch_id)
);

CREATE TABLE IF NOT EXISTS rule_findings (
    run_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    metric TEXT NOT NULL,
    observed REAL NOT NULL,
    threshold_value REAL NOT NULL,
    message TEXT NOT NULL,
    PRIMARY KEY (run_id, rule_id),
    FOREIGN KEY (run_id) REFERENCES detection_runs(run_id) ON DELETE CASCADE
);
"""


class SQLiteAnomalyStore:
    """Local audit store with one committed result per dataset batch."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def save(self, result: DetectionResult) -> None:
        import json

        record = result.as_record()
        metrics_json = json.dumps(result.snapshot.feature_dict(), sort_keys=True)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT run_id FROM detection_runs WHERE dataset = ? AND batch_id = ?",
                (result.snapshot.dataset, result.snapshot.batch_id),
            ).fetchone()
            if existing and existing[0] != result.run_id:
                connection.execute("DELETE FROM detection_runs WHERE run_id = ?", (existing[0],))

            connection.execute(
                """
                INSERT OR REPLACE INTO detection_runs (
                    run_id, dataset, batch_id, observed_at, row_count, metrics_json,
                    model_score, model_anomaly, is_anomaly, final_severity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.run_id,
                    record["dataset"],
                    record["batch_id"],
                    record["observed_at"],
                    record["row_count"],
                    metrics_json,
                    record["model_score"],
                    int(record["model_anomaly"]),
                    int(record["is_anomaly"]),
                    record["final_severity"],
                ),
            )
            connection.execute("DELETE FROM rule_findings WHERE run_id = ?", (result.run_id,))
            connection.executemany(
                """
                INSERT INTO rule_findings (
                    run_id, rule_id, severity, metric, observed, threshold_value, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        result.run_id,
                        finding.rule_id,
                        finding.severity.name,
                        finding.metric,
                        finding.observed,
                        finding.threshold,
                        finding.message,
                    )
                    for finding in result.findings
                ],
            )

    def count_runs(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) FROM detection_runs").fetchone()
        return int(row[0]) if row else 0
