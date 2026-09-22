from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

from anomaly_pipeline.config import ModelConfig
from anomaly_pipeline.domain import MetricSnapshot


class ModelValidationError(ValueError):
    """Raised when feature data or a stored model is incompatible."""


@dataclass(frozen=True)
class ModelPrediction:
    score: float
    is_anomaly: bool


@dataclass
class ModelBundle:
    feature_names: tuple[str, ...]
    estimator: Any


def _feature_frame(history: pd.DataFrame, features: tuple[str, ...]) -> pd.DataFrame:
    missing = sorted(set(features) - set(history.columns))
    if missing:
        raise ModelValidationError(f"Missing model features: {', '.join(missing)}")

    frame = cast(
        pd.DataFrame,
        history.loc[:, list(features)].apply(pd.to_numeric, errors="coerce"),
    )
    if frame.isna().any().any():
        raise ModelValidationError("Model features contain missing or non-numeric values")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ModelValidationError("Model features contain infinite values")
    return frame


def train_model(history: pd.DataFrame, config: ModelConfig) -> ModelBundle:
    if len(history) < config.minimum_training_rows:
        raise ModelValidationError(
            f"At least {config.minimum_training_rows} history rows are required; got {len(history)}"
        )
    features = _feature_frame(history, config.features)
    estimator = Pipeline(
        steps=[
            ("scale", RobustScaler()),
            (
                "detect",
                IsolationForest(
                    contamination=config.contamination,
                    n_estimators=200,
                    random_state=config.random_state,
                    n_jobs=1,
                ),
            ),
        ]
    )
    estimator.fit(features)
    return ModelBundle(feature_names=config.features, estimator=estimator)


def predict(bundle: ModelBundle, snapshot: MetricSnapshot) -> ModelPrediction:
    available = snapshot.feature_dict()
    missing = sorted(set(bundle.feature_names) - set(available))
    if missing:
        raise ModelValidationError(f"Snapshot does not provide features: {', '.join(missing)}")
    feature_row = pd.DataFrame(
        [[available[name] for name in bundle.feature_names]], columns=list(bundle.feature_names)
    )
    score = -float(bundle.estimator.decision_function(feature_row)[0])
    prediction = int(bundle.estimator.predict(feature_row)[0])
    return ModelPrediction(score=score, is_anomaly=prediction == -1)


def save_model(bundle: ModelBundle, path: str | Path) -> None:
    model_path = Path(path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)


def load_model(path: str | Path) -> ModelBundle:
    model_path = Path(path)
    if not model_path.is_file():
        raise ModelValidationError(f"Model file not found: {model_path}")
    bundle = joblib.load(model_path)
    if not isinstance(bundle, ModelBundle):
        raise ModelValidationError("Stored artifact is not a compatible ModelBundle")
    return bundle
