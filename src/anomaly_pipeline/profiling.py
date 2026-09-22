from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd

from anomaly_pipeline.config import DatasetConfig
from anomaly_pipeline.domain import MetricSnapshot


def _blank_or_null(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    return text.isna() | text.str.strip().eq("")


def profile_batch(
    frame: pd.DataFrame,
    config: DatasetConfig,
    *,
    batch_id: str,
    observed_at: datetime | None = None,
) -> MetricSnapshot:
    """Convert a normalized batch into stable dataset-level model features."""
    if frame.empty:
        raise ValueError("Cannot profile an empty batch")

    observed = observed_at or datetime.now(UTC)
    observed = observed.replace(tzinfo=UTC) if observed.tzinfo is None else observed.astimezone(UTC)

    row_count = len(frame)
    duplicate_rate = float(frame[config.id_column].duplicated(keep=False).mean())
    null_member_rate = float(_blank_or_null(frame[config.member_column]).mean())

    amounts = frame[config.amount_column]
    invalid_amount_rate = float((amounts.isna() | amounts.lt(0)).mean())
    valid_amounts = amounts[amounts.notna() & amounts.ge(0)]
    mean_amount = float(valid_amounts.mean()) if not valid_amounts.empty else 0.0
    p95_amount = float(valid_amounts.quantile(0.95)) if not valid_amounts.empty else 0.0

    statuses = frame[config.status_column].astype("string").str.upper()
    invalid_status_rate = float(
        (statuses.isna() | statuses.eq("") | ~statuses.isin(config.allowed_statuses)).mean()
    )

    timestamps = frame[config.timestamp_column]
    invalid_timestamp_rate = float(timestamps.isna().mean())
    valid_timestamps = timestamps.dropna()
    if valid_timestamps.empty:
        freshness_hours = 1_000_000.0
    else:
        latest = valid_timestamps.max().to_pydatetime()
        freshness_hours = max(0.0, (observed - latest).total_seconds() / 3600)

    values = (
        duplicate_rate,
        null_member_rate,
        invalid_amount_rate,
        invalid_status_rate,
        invalid_timestamp_rate,
        mean_amount,
        p95_amount,
        freshness_hours,
    )
    if not all(np.isfinite(value) for value in values):
        raise ValueError("Profiling produced non-finite metrics")

    return MetricSnapshot(
        dataset=config.name,
        batch_id=batch_id,
        observed_at=observed,
        row_count=row_count,
        duplicate_rate=duplicate_rate,
        null_member_rate=null_member_rate,
        invalid_amount_rate=invalid_amount_rate,
        invalid_status_rate=invalid_status_rate,
        invalid_timestamp_rate=invalid_timestamp_rate,
        mean_amount=mean_amount,
        p95_amount=p95_amount,
        freshness_hours=freshness_hours,
    )
