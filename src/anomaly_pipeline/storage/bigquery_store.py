from __future__ import annotations

from collections.abc import Callable
from typing import Any

from anomaly_pipeline.domain import DetectionResult


class BigQueryWriteError(RuntimeError):
    """Raised when BigQuery rejects one or more audit rows."""


class BigQueryAnomalyStore:
    """Optional production sink. Authentication uses Application Default Credentials."""

    def __init__(
        self,
        project_id: str,
        dataset: str,
        *,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        if client_factory is None:
            try:
                from google.cloud import bigquery
            except ImportError as exc:
                raise RuntimeError("Install the 'gcp' extra to use the BigQuery sink") from exc
            client_factory = bigquery.Client
        self.client = client_factory(project=project_id)
        self.run_table = f"{project_id}.{dataset}.detection_runs"
        self.finding_table = f"{project_id}.{dataset}.rule_findings"

    def save(self, result: DetectionResult) -> None:
        run_row = result.as_record()
        run_row["metrics"] = result.snapshot.feature_dict()
        run_errors = self.client.insert_rows_json(
            self.run_table, [run_row], row_ids=[result.run_id]
        )
        if run_errors:
            raise BigQueryWriteError(f"Failed to write detection run: {run_errors}")

        if result.findings:
            rows = [{"run_id": result.run_id, **finding.as_record()} for finding in result.findings]
            row_ids = [f"{result.run_id}:{finding.rule_id}" for finding in result.findings]
            finding_errors = self.client.insert_rows_json(self.finding_table, rows, row_ids=row_ids)
            if finding_errors:
                raise BigQueryWriteError(f"Failed to write rule findings: {finding_errors}")
