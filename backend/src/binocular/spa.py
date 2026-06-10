"""SPA serving utilities for the React frontend."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Default location where the Dockerfile copies the frontend dist/ output.
DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static_dist"


def mount_spa(app: FastAPI, static_dir: Path | None = None) -> None:
    """Mount the built SPA on the FastAPI app.

    Serves ``index.html`` for any path that does not match an existing
    static asset or an ``/api`` route, enabling client-side routing.

    Args:
        app: The FastAPI application instance.
        static_dir: Directory containing the Vite ``dist/`` output.
            Defaults to ``<project_root>/static_dist/``.
    """
    dist = static_dir or DEFAULT_STATIC_DIR

    if not dist.is_dir():
        return  # No frontend build available — skip mounting

    # Mount static assets (JS, CSS, fonts, images) under /assets/
    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="static-assets",
        )

    # Serve favicon and other root-level static files
    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(str(dist / "favicon.svg"))

    # SPA catch-all: return index.html for any non-API path
    @app.get("/{path:path}", include_in_schema=False)
    async def spa_catchall(path: str) -> FileResponse:
        # If the requested file exists in dist/, serve it directly
        requested = dist / path
        if requested.is_file() and ".." not in path:
            return FileResponse(str(requested))
        # Otherwise, return index.html for client-side routing
        return FileResponse(str(dist / "index.html"))
