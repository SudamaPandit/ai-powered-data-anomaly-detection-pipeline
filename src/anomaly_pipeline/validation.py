from __future__ import annotations

import pandas as pd

from anomaly_pipeline.config import DatasetConfig


class SchemaValidationError(ValueError):
    """Raised when a batch cannot be profiled safely."""


def prepare_claims(frame: pd.DataFrame, config: DatasetConfig) -> pd.DataFrame:
    """Validate structural requirements and normalize types without hiding bad rows."""
    missing = sorted(set(config.required_columns) - set(frame.columns))
    if missing:
        raise SchemaValidationError(f"Missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise SchemaValidationError("Input batch is empty")

    cleaned = frame.loc[:, list(config.required_columns)].copy()
    string_columns = [
        config.id_column,
        config.member_column,
        config.status_column,
        "provider_id",
        "diagnosis_code",
        "source_system",
    ]
    for column in string_columns:
        if column in cleaned.columns:
            cleaned[column] = cleaned[column].astype("string").str.strip()

    cleaned[config.amount_column] = pd.to_numeric(cleaned[config.amount_column], errors="coerce")
    cleaned[config.timestamp_column] = pd.to_datetime(
        cleaned[config.timestamp_column], errors="coerce", utc=True, format="mixed"
    )
    cleaned[config.service_date_column] = pd.to_datetime(
        cleaned[config.service_date_column], errors="coerce", utc=True, format="mixed"
    )
    return cleaned
