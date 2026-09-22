from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any
from urllib.request import Request, urlopen

from anomaly_pipeline.domain import DetectionResult, Severity

LOGGER = logging.getLogger(__name__)


def build_alert(result: DetectionResult) -> dict[str, object]:
    return {
        "text": (
            f"[{result.final_severity.name}] Data anomaly detected in "
            f"{result.snapshot.dataset} batch {result.snapshot.batch_id}"
        ),
        "run_id": result.run_id,
        "model_anomaly": result.model_anomaly,
        "model_score": round(result.model_score, 6),
        "rules": [finding.rule_id for finding in result.findings],
    }


def send_webhook(
    result: DetectionResult,
    webhook_url: str,
    *,
    minimum_severity: Severity = Severity.HIGH,
    opener: Callable[..., Any] = urlopen,
) -> bool:
    """Send one concise Slack-compatible payload for actionable results."""
    if not result.is_anomaly or result.final_severity < minimum_severity:
        return False
    if not webhook_url.startswith("https://"):
        raise ValueError("Webhook URL must use HTTPS")

    request = Request(
        webhook_url,
        data=json.dumps(build_alert(result)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener(request, timeout=5) as response:
        status = getattr(response, "status", 200)
        if status >= 300:
            raise RuntimeError(f"Webhook returned HTTP {status}")
    LOGGER.info("Anomaly alert delivered", extra={"run_id": result.run_id})
    return True
