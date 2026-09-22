from __future__ import annotations

import json

import pytest

from anomaly_pipeline.alerts import build_alert, send_webhook
from anomaly_pipeline.domain import DetectionResult, MetricSnapshot, Severity


def make_result(snapshot: MetricSnapshot, severity: Severity) -> DetectionResult:
    return DetectionResult(
        run_id="run-1",
        snapshot=snapshot,
        model_score=0.123456789,
        model_anomaly=True,
        final_severity=severity,
    )


def test_builds_concise_payload(normal_snapshot: MetricSnapshot) -> None:
    payload = build_alert(make_result(normal_snapshot, Severity.HIGH))
    assert payload["run_id"] == "run-1"
    assert "healthcare_claims_feed" in str(payload["text"])
    assert payload["model_score"] == 0.123457


def test_skips_below_threshold(normal_snapshot: MetricSnapshot) -> None:
    called = False

    def opener(*_: object, **__: object) -> object:
        nonlocal called
        called = True
        raise AssertionError

    assert not send_webhook(
        make_result(normal_snapshot, Severity.MEDIUM), "https://example.com", opener=opener
    )
    assert not called


def test_rejects_insecure_webhook(normal_snapshot: MetricSnapshot) -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        send_webhook(make_result(normal_snapshot, Severity.HIGH), "http://example.com")


def test_sends_json_payload(normal_snapshot: MetricSnapshot) -> None:
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    def opener(request: object, timeout: int) -> Response:
        captured["data"] = request.data
        captured["timeout"] = timeout
        return Response()

    assert send_webhook(
        make_result(normal_snapshot, Severity.HIGH),
        "https://example.com/hook",
        opener=opener,
    )
    assert json.loads(captured["data"])["run_id"] == "run-1"
    assert captured["timeout"] == 5
