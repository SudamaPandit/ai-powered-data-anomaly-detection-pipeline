from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from anomaly_pipeline.config import PipelineConfig
from anomaly_pipeline.detection.model import (
    ModelBundle,
    ModelValidationError,
    load_model,
    predict,
    save_model,
    train_model,
)
from anomaly_pipeline.domain import MetricSnapshot


def test_trains_and_scores_snapshot(
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
    normal_snapshot: MetricSnapshot,
) -> None:
    bundle = train_model(normal_history, pipeline_config.model)
    prediction = predict(bundle, normal_snapshot)
    assert isinstance(prediction.score, float)
    assert isinstance(prediction.is_anomaly, bool)


def test_persists_model_bundle(
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.joblib"
    original = train_model(normal_history, pipeline_config.model)
    save_model(original, path)
    restored = load_model(path)
    assert restored.feature_names == original.feature_names


def test_rejects_short_history(
    normal_history: pd.DataFrame, pipeline_config: PipelineConfig
) -> None:
    with pytest.raises(ModelValidationError, match="At least"):
        train_model(normal_history.head(2), pipeline_config.model)


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, "bad"])
def test_rejects_invalid_training_features(
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
    bad_value: object,
) -> None:
    history = normal_history.copy()
    history["row_count"] = history["row_count"].astype(object)
    history.loc[0, "row_count"] = bad_value
    message = "infinite" if bad_value is np.inf else "missing or non-numeric"
    with pytest.raises(ModelValidationError, match=message):
        train_model(history, pipeline_config.model)


def test_rejects_missing_model_file(tmp_path: Path) -> None:
    with pytest.raises(ModelValidationError, match="not found"):
        load_model(tmp_path / "missing.joblib")


def test_rejects_incompatible_artifact(tmp_path: Path) -> None:
    import joblib

    path = tmp_path / "bad.joblib"
    joblib.dump({"not": "a model"}, path)
    with pytest.raises(ModelValidationError, match="compatible"):
        load_model(path)


def test_rejects_bundle_feature_not_in_snapshot(normal_snapshot: MetricSnapshot) -> None:
    class NeverCalled:
        pass

    bundle = ModelBundle(feature_names=("unknown_feature",), estimator=NeverCalled())
    with pytest.raises(ModelValidationError, match="unknown_feature"):
        predict(bundle, normal_snapshot)
