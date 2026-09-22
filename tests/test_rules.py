from __future__ import annotations

from dataclasses import replace

import pandas as pd

from anomaly_pipeline.config import PipelineConfig, RuleThreshold
from anomaly_pipeline.detection.rules import enabled_rule_ids, evaluate_rules
from anomaly_pipeline.domain import MetricSnapshot, Severity


def test_no_findings_for_normal_snapshot(
    normal_snapshot: MetricSnapshot,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    assert evaluate_rules(normal_snapshot, normal_history, pipeline_config.rules) == ()


def test_detects_direct_rate_breach(
    normal_snapshot: MetricSnapshot,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    snapshot = replace(normal_snapshot, duplicate_rate=0.25)
    findings = evaluate_rules(snapshot, normal_history, pipeline_config.rules)
    assert findings[0].rule_id == "duplicate_rate"
    assert findings[0].severity is Severity.HIGH


def test_detects_volume_and_amount_shift(
    normal_snapshot: MetricSnapshot,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    snapshot = replace(normal_snapshot, row_count=500, mean_amount=500)
    findings = evaluate_rules(snapshot, normal_history, pipeline_config.rules)
    ids = {finding.rule_id for finding in findings}
    assert ids == {"volume_drop_rate", "mean_amount_shift_rate"}


def test_disabled_rule_is_skipped(
    normal_snapshot: MetricSnapshot,
    normal_history: pd.DataFrame,
    pipeline_config: PipelineConfig,
) -> None:
    rules = dict(pipeline_config.rules)
    rules["duplicate_rate"] = RuleThreshold(False, 0.0, Severity.CRITICAL)
    findings = evaluate_rules(replace(normal_snapshot, duplicate_rate=0.8), normal_history, rules)
    assert "duplicate_rate" not in {finding.rule_id for finding in findings}


def test_lists_only_enabled_rules(pipeline_config: PipelineConfig) -> None:
    rules = dict(pipeline_config.rules)
    rules["duplicate_rate"] = RuleThreshold(False, 0.0, Severity.LOW)
    assert "duplicate_rate" not in set(enabled_rule_ids(rules))
