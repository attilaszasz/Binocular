"""Integration tests for SPA static file fallback serving."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from backend.src.api.dependencies import get_settings as get_api_settings
from backend.src.config import get_settings
from backend.src.main import create_app


@pytest.fixture
def app(db_path: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> FastAPI:
    """Create app with isolated DB and temporary frontend dist directory."""

    monkeypatch.setenv("BINOCULAR_DB_PATH", db_path)
    get_settings.cache_clear()
    get_api_settings.cache_clear()

    dist_dir = tmp_path / "frontend-dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text("<html><body>Binocular SPA</body></html>", encoding="utf-8")

    return create_app(frontend_dist=dist_dir)


async def test_spa_fallback_serves_index_for_deep_links(client: AsyncClient) -> None:
    """GET on non-API deep links should return index.html content."""

    response = await client.get("/modules")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Binocular SPA" in response.text


async def test_api_routes_remain_available_with_spa_fallback(client: AsyncClient) -> None:
    """API endpoints should keep normal behavior when SPA fallback is enabled."""

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
