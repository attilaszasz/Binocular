"""Static SPA serving integration."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

STATIC_DIST_DIR = Path(__file__).parent / "static_dist"
SPA_RESERVED_PREFIXES = ("api/", "healthz", "docs", "redoc", "openapi.json")


def mount_spa(app: FastAPI, static_dir: Path = STATIC_DIST_DIR) -> bool:
    """Mount built SPA assets when they are available."""

    index_path = static_dir / "index.html"
    if not index_path.is_file():
        return False

    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str) -> FileResponse:
        if spa_path.startswith(SPA_RESERVED_PREFIXES):
            raise HTTPException(status_code=404)
        return FileResponse(index_path)

    return True
