"""Module Kit REST API routes.

Serves the AI Module Kit static files for module authoring guidance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/v1", tags=["module-kit"])

# Kit files directory — sibling package to routes.
_KIT_DIR = Path(__file__).resolve().parent.parent / "module_kit"

# Mapping of filename → description for the listing endpoint.
_KIT_FILES: dict[str, str] = {
    "STARTER_TEMPLATE.py": "Annotated V1 contract skeleton — copy and customise",
    "EXAMPLE_MODULE.py": "Working example based on Sony Alpha firmware detection",
    "AI_INSTRUCTIONS.md": "Structured AI authoring guide with test harness",
    "CONTRACT_REFERENCE.md": "V1 authoring contract documentation",
}

# Media types for download responses.
_MEDIA_TYPES: dict[str, str] = {
    ".py": "text/x-python",
    ".md": "text/markdown",
}


@router.get("/module-kit/")
async def list_kit_files() -> dict[str, Any]:
    """List available AI Module Kit files with download URLs."""
    if not _KIT_DIR.is_dir():
        raise HTTPException(
            status_code=500,
            detail="Module kit directory not found",
        )

    files: list[dict[str, Any]] = []
    for name, description in _KIT_FILES.items():
        path = _KIT_DIR / name
        if path.is_file():
            files.append(
                {
                    "name": name,
                    "description": description,
                    "size_bytes": path.stat().st_size,
                    "url": f"/api/v1/module-kit/{name}",
                }
            )

    return {"files": files}


@router.get("/module-kit/{filename}")
async def download_kit_file(filename: str) -> FileResponse:
    """Download an individual kit file."""
    # Prevent path traversal.
    safe_name = Path(filename).name
    if safe_name != filename or filename not in _KIT_FILES:
        raise HTTPException(
            status_code=404,
            detail=f"Kit file not found: {filename}",
        )

    path = _KIT_DIR / safe_name
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Kit file not found: {filename}",
        )

    suffix = path.suffix.lower()
    media_type = _MEDIA_TYPES.get(suffix, "application/octet-stream")

    return FileResponse(
        path=path,
        filename=safe_name,
        media_type=media_type,
    )
