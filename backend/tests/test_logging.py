import json

import pytest
import structlog

from binocular.logging import configure_logging


def test_configure_logging_emits_json_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    logger = structlog.get_logger("binocular.test")

    logger.info("startup_test", service="binocular")

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["event"] == "startup_test"
    assert payload["service"] == "binocular"
    assert payload["level"] == "info"
    assert payload["logger"] == "binocular.test"
    assert "timestamp" in payload


def test_configure_logging_preserves_exception_details(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    logger = structlog.get_logger("binocular.test")

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("exception_test")

    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "exception_test"
    assert "RuntimeError: boom" in payload["exception"]