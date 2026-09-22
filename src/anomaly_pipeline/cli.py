from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import pandas as pd

from anomaly_pipeline.alerts import send_webhook
from anomaly_pipeline.config import load_config
from anomaly_pipeline.detection.model import load_model, save_model, train_model
from anomaly_pipeline.domain import DetectionResult
from anomaly_pipeline.logging_config import configure_logging
from anomaly_pipeline.pipeline import run_detection
from anomaly_pipeline.storage.base import AnomalyStore
from anomaly_pipeline.storage.bigquery_store import BigQueryAnomalyStore
from anomaly_pipeline.storage.sqlite_store import SQLiteAnomalyStore


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anomaly-pipeline",
        description="Profile a data feed and detect rule-based and multivariate anomalies.",
    )
    parser.add_argument("--log-level", default="INFO")
    commands = parser.add_subparsers(dest="command", required=True)

    train = commands.add_parser("train", help="Train a model from normal historical metrics")
    train.add_argument("--history", required=True, type=Path)
    train.add_argument("--config", default=Path("config/claims.yml"), type=Path)
    train.add_argument("--model", required=True, type=Path)

    detect = commands.add_parser("detect", help="Detect anomalies in one CSV batch")
    detect.add_argument("--input", required=True, type=Path)
    detect.add_argument("--history", required=True, type=Path)
    detect.add_argument("--config", default=Path("config/claims.yml"), type=Path)
    detect.add_argument("--model", required=True, type=Path)
    detect.add_argument("--sink", choices=("sqlite", "bigquery"), default="sqlite")
    detect.add_argument("--store", type=Path, default=Path("data/anomalies.db"))
    detect.add_argument("--as-of", help="UTC ISO timestamp used for reproducible freshness checks")
    detect.add_argument("--alert", action="store_true", help="Send HIGH/CRITICAL result to webhook")
    return parser


def _store(args: argparse.Namespace) -> AnomalyStore:
    if args.sink == "sqlite":
        return SQLiteAnomalyStore(args.store)
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BIGQUERY_DATASET", "data_observability")
    if not project_id:
        raise ValueError("GCP_PROJECT_ID is required for the BigQuery sink")
    return BigQueryAnomalyStore(project_id, dataset)


def _print_result(result: DetectionResult) -> None:
    output: dict[str, Any] = result.as_record()
    output["findings"] = [finding.as_record() for finding in result.findings]
    print(json.dumps(output, indent=2, default=str))


def main(argv: list[str] | None = None) -> None:
    parser = _parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    config = load_config(args.config)
    history = pd.read_csv(args.history)

    if args.command == "train":
        bundle = train_model(history, config.model)
        save_model(bundle, args.model)
        print(f"Model trained with {len(history)} historical snapshots and saved to {args.model}")
        return

    model = load_model(args.model)
    observed_at = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")) if args.as_of else None
    webhook_url = os.getenv("ANOMALY_SLACK_WEBHOOK_URL")

    alert = None
    if args.alert:
        if not webhook_url:
            parser.error("ANOMALY_SLACK_WEBHOOK_URL is required when --alert is used")
        alert = partial(send_webhook, webhook_url=webhook_url)

    result = run_detection(
        args.input,
        history,
        config,
        model,
        _store(args),
        observed_at=observed_at,
        alert=alert,
    )
    _print_result(result)
