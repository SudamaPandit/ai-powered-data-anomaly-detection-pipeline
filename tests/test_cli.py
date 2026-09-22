from __future__ import annotations

from pathlib import Path

import pytest

from anomaly_pipeline.cli import main


def test_train_command_creates_model(project_root: Path, tmp_path: Path) -> None:
    model = tmp_path / "model.joblib"
    main(
        [
            "--log-level",
            "WARNING",
            "train",
            "--history",
            str(project_root / "data/sample/historical_metrics.csv"),
            "--config",
            str(project_root / "config/claims.yml"),
            "--model",
            str(model),
        ]
    )
    assert model.is_file()


def test_detect_command_outputs_result(
    project_root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = tmp_path / "model.joblib"
    config = project_root / "config/claims.yml"
    history = project_root / "data/sample/historical_metrics.csv"
    main(["train", "--history", str(history), "--config", str(config), "--model", str(model)])
    capsys.readouterr()
    main(
        [
            "detect",
            "--input",
            str(project_root / "data/sample/claims_current.csv"),
            "--history",
            str(history),
            "--config",
            str(config),
            "--model",
            str(model),
            "--store",
            str(tmp_path / "audit.db"),
            "--as-of",
            "2026-09-22T12:00:00Z",
        ]
    )
    assert '"dataset": "healthcare_claims_feed"' in capsys.readouterr().out
