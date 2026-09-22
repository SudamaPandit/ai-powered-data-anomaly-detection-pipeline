from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pandas as pd

from anomaly_pipeline.config import PipelineConfig
from anomaly_pipeline.detection.model import ModelBundle, predict
from anomaly_pipeline.detection.rules import evaluate_rules
from anomaly_pipeline.detection.scoring import final_severity
from anomaly_pipeline.domain import DetectionResult
from anomaly_pipeline.profiling import profile_batch
from anomaly_pipeline.storage.base import AnomalyStore
from anomaly_pipeline.validation import prepare_claims

LOGGER = logging.getLogger(__name__)


def file_batch_id(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def run_detection(
    input_path: str | Path,
    history: pd.DataFrame,
    config: PipelineConfig,
    model: ModelBundle,
    store: AnomalyStore,
    *,
    observed_at: datetime | None = None,
    alert: Callable[[DetectionResult], object] | None = None,
) -> DetectionResult:
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input batch not found: {path}")

    batch_id = file_batch_id(path)
    run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{config.dataset.name}:{batch_id}"))
    context = {"run_id": run_id, "dataset": config.dataset.name, "batch_id": batch_id}
    LOGGER.info("Starting anomaly detection", extra=context)

    raw = pd.read_csv(path)
    prepared = prepare_claims(raw, config.dataset)
    snapshot = profile_batch(
        prepared,
        config.dataset,
        batch_id=batch_id,
        observed_at=observed_at,
    )
    findings = evaluate_rules(snapshot, history, config.rules)
    prediction = predict(model, snapshot)
    severity = final_severity(findings, prediction.is_anomaly)

    result = DetectionResult(
        run_id=run_id,
        snapshot=snapshot,
        model_score=prediction.score,
        model_anomaly=prediction.is_anomaly,
        final_severity=severity,
        findings=findings,
    )
    store.save(result)
    if alert is not None:
        alert(result)
    LOGGER.info(
        "Anomaly detection completed",
        extra=context,
    )
    return result
