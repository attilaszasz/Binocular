"""Isolated browser server: temporary volumes, fixture-only HTTP, no real alerts."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI

from binocular.app import create_app
from binocular.config import Settings
from binocular.scraping.client import ScrapeClient


def create_e2e_app() -> FastAPI:
    volume = tempfile.TemporaryDirectory(prefix="binocular-browser-")
    root = Path(volume.name)
    app = create_app(Settings(data_dir=root, modules_dir=root / "modules"))
    original = app.router.lifespan_context

    def offline(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if str(request.url) == "https://alphauniverse.com/firmware/":
            fixture = (
                Path(__file__).parent
                / "fixtures/sony_alpha/alpha_universe_firmware.html"
            )
            return httpx.Response(200, text=fixture.read_text())
        raise AssertionError(f"Unscripted outbound request blocked: {request.url}")

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        client = ScrapeClient(transport=httpx.MockTransport(offline), default_delay=0)
        with (
            patch("binocular.app.ScrapeClient", return_value=client),
            patch(
                "binocular.services.notifier.NotifierService.send_notification",
                new=AsyncMock(return_value=True),
            ),
        ):
            async with original(application):
                # Browser smoke exercises manual workflows. Automatic races are
                # deterministic tests; no unrequested checks run in this server.
                await application.state.scheduler.stop()
                yield
        volume.cleanup()

    app.router.lifespan_context = lifespan
    return app
