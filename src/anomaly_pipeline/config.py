from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from anomaly_pipeline.domain import Severity


class ConfigurationError(ValueError):
    """Raised when a pipeline configuration is incomplete or invalid."""


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    id_column: str
    member_column: str
    amount_column: str
    status_column: str
    timestamp_column: str
    service_date_column: str
    required_columns: tuple[str, ...]
    allowed_statuses: frozenset[str]


@dataclass(frozen=True)
class RuleThreshold:
    enabled: bool
    threshold: float
    severity: Severity


@dataclass(frozen=True)
class ModelConfig:
    features: tuple[str, ...]
    contamination: float
    random_state: int
    minimum_training_rows: int


@dataclass(frozen=True)
class PipelineConfig:
    dataset: DatasetConfig
    rules: dict[str, RuleThreshold]
    model: ModelConfig


def _required(mapping: dict[str, Any], key: str, section: str) -> Any:
    if key not in mapping:
        raise ConfigurationError(f"Missing '{key}' in '{section}' configuration")
    return mapping[key]


def load_config(path: str | Path) -> PipelineConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    with config_path.open(encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    if not isinstance(raw, dict):
        raise ConfigurationError("Configuration root must be a mapping")

    dataset_raw = _required(raw, "dataset", "root")
    rules_raw = _required(raw, "rules", "root")
    model_raw = _required(raw, "model", "root")
    if not all(isinstance(section, dict) for section in (dataset_raw, rules_raw, model_raw)):
        raise ConfigurationError("dataset, rules and model must be mappings")

    required_columns = tuple(_required(dataset_raw, "required_columns", "dataset"))
    allowed_statuses = frozenset(_required(dataset_raw, "allowed_statuses", "dataset"))
    if not required_columns or not allowed_statuses:
        raise ConfigurationError("required_columns and allowed_statuses cannot be empty")

    dataset = DatasetConfig(
        name=str(_required(dataset_raw, "name", "dataset")),
        id_column=str(_required(dataset_raw, "id_column", "dataset")),
        member_column=str(_required(dataset_raw, "member_column", "dataset")),
        amount_column=str(_required(dataset_raw, "amount_column", "dataset")),
        status_column=str(_required(dataset_raw, "status_column", "dataset")),
        timestamp_column=str(_required(dataset_raw, "timestamp_column", "dataset")),
        service_date_column=str(_required(dataset_raw, "service_date_column", "dataset")),
        required_columns=required_columns,
        allowed_statuses=allowed_statuses,
    )

    rules: dict[str, RuleThreshold] = {}
    for rule_id, rule_raw in rules_raw.items():
        if not isinstance(rule_raw, dict):
            raise ConfigurationError(f"Rule '{rule_id}' must be a mapping")
        rules[str(rule_id)] = RuleThreshold(
            enabled=bool(rule_raw.get("enabled", True)),
            threshold=float(_required(rule_raw, "threshold", f"rules.{rule_id}")),
            severity=Severity.from_name(str(_required(rule_raw, "severity", f"rules.{rule_id}"))),
        )

    contamination = float(_required(model_raw, "contamination", "model"))
    if not 0 < contamination <= 0.5:
        raise ConfigurationError("model.contamination must be greater than 0 and at most 0.5")

    model = ModelConfig(
        features=tuple(_required(model_raw, "features", "model")),
        contamination=contamination,
        random_state=int(model_raw.get("random_state", 42)),
        minimum_training_rows=int(model_raw.get("minimum_training_rows", 20)),
    )
    if not model.features:
        raise ConfigurationError("model.features cannot be empty")

    return PipelineConfig(dataset=dataset, rules=rules, model=model)
