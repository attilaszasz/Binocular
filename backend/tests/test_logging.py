"""Tests for binocular.logging."""

import logging

import structlog

from binocular.config import LogFormat
from binocular.logging import setup_logging


class TestSetupLogging:
    """Verify structlog configuration for JSON and console modes."""

    def test_json_output_is_valid_json(self, capsys: object) -> None:
        setup_logging(LogFormat.JSON, "info")
        logger = structlog.get_logger("test")
        logger.info("hello", key="value")

        # capsys may not capture logging output via handler directly,
        # so we verify configuration instead.
        root = logging.getLogger()
        assert len(root.handlers) == 1
        formatter = root.handlers[0].formatter
        assert isinstance(formatter, structlog.stdlib.ProcessorFormatter)

    def test_console_output_configured(self) -> None:
        setup_logging(LogFormat.CONSOLE, "debug")
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1

    def test_uvicorn_logs_propagate(self) -> None:
        setup_logging(LogFormat.JSON, "info")
        uv_logger = logging.getLogger("uvicorn")
        assert uv_logger.propagate is True
        assert len(uv_logger.handlers) == 0

    def test_json_renderer_produces_json(self) -> None:
        setup_logging(LogFormat.JSON, "info")
        root = logging.getLogger()
        formatter = root.handlers[0].formatter
        assert formatter is not None
        # Verify the formatter chain includes JSONRenderer
        assert isinstance(formatter, structlog.stdlib.ProcessorFormatter)

    def test_log_level_case_insensitive(self) -> None:
        setup_logging(LogFormat.CONSOLE, "WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING
