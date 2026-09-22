from __future__ import annotations

from pathlib import Path

import pytest

from anomaly_pipeline.config import ConfigurationError, load_config
from anomaly_pipeline.domain import Severity


def test_loads_claim_configuration(project_root: Path) -> None:
    config = load_config(project_root / "config" / "claims.yml")
    assert config.dataset.name == "healthcare_claims_feed"
    assert config.rules["invalid_amount_rate"].severity is Severity.CRITICAL
    assert "row_count" in config.model.features


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_config(tmp_path / "missing.yml")


def test_rejects_non_mapping_root(tmp_path: Path) -> None:
    path = tmp_path / "bad.yml"
    path.write_text("- invalid\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="root must be a mapping"):
        load_config(path)


def test_rejects_invalid_contamination(project_root: Path, tmp_path: Path) -> None:
    text = (project_root / "config" / "claims.yml").read_text(encoding="utf-8")
    path = tmp_path / "bad.yml"
    path.write_text(text.replace("contamination: 0.05", "contamination: 0.9"), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="contamination"):
        load_config(path)


def test_rejects_unknown_severity() -> None:
    with pytest.raises(ValueError, match="Unsupported severity"):
        Severity.from_name("urgent")
