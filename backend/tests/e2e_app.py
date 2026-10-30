"""Isolated browser server: temporary volumes, fixture-only HTTP, no real alerts."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from binocular.app import create_app
from binocular.config import Settings
from binocular.scraping.client import ScrapeClient


def create_e2e_app() -> FastAPI:
    volume = tempfile.TemporaryDirectory(prefix="binocular-browser-")
    root = Path(volume.name)
    app = create_app(Settings(data_dir=root, modules_dir=root / "modules"))
    original = app.router.lifespan_context
    # Count transport calls (including robots) so browser tests prove that local
    # interaction does not merely hide manufacturer work behind a local API.
    vendor_requests = 0
    vendor_failure = False

    @app.put("/api/v1/e2e/vendor-failure/{enabled}")
    async def set_vendor_failure(enabled: bool) -> dict[str, bool]:
        """Fixture-only control; never registered on the production application."""
        nonlocal vendor_failure
        vendor_failure = enabled
        return {"enabled": enabled}

    @app.middleware("http")
    async def request_count(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-E2E-Vendor-Requests"] = str(vendor_requests)
        return response

    def offline(request: httpx.Request) -> httpx.Response:
        nonlocal vendor_requests
        vendor_requests += 1
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\n")
        if str(request.url) == "https://alphauniverse.com/firmware/":
            if vendor_failure:
                return httpx.Response(200, text="<html>Unavailable fixture</html>")
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
