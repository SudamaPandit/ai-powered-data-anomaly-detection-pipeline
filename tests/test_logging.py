from __future__ import annotations

import json
import logging

from anomaly_pipeline.logging_config import JsonFormatter, configure_logging


def test_json_formatter_includes_context() -> None:
    record = logging.LogRecord("pipeline", logging.INFO, __file__, 1, "completed", (), None)
    record.run_id = "run-1"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "completed"
    assert payload["run_id"] == "run-1"


def test_configure_logging_replaces_root_handlers() -> None:
    configure_logging("WARNING")
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert len(root.handlers) == 1
