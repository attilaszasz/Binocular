"""Module Development Kit file serving routes."""

import io
import zipfile
from pathlib import Path
from typing import Final

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/module-kit", tags=["module-kit"])

_KIT_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "module_kit"

_KIT_FILES: Final[dict[str, str]] = {
    "CONTRACT_REFERENCE.md": "Authoring contract reference",
    "STARTER_TEMPLATE.py": "Minimal starter module template",
    "EXAMPLE_MODULE.py": "Working example module",
    "AI_INSTRUCTIONS.md": "AI coding tool instructions",
}

_CONTENT_TYPES: Final[dict[str, str]] = {
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/x-python; charset=utf-8",
}

# Cached zip bundle (generated on first request)
_zip_cache: bytes | None = None


class KitFileInfo(BaseModel):
    """Metadata for a single kit file."""

    filename: str
    description: str
    download_url: str = Field(alias="downloadUrl")

    model_config = ConfigDict(populate_by_name=True)


class KitFileListResponse(BaseModel):
    """List of available kit files."""

    files: list[KitFileInfo]
    bundle_url: str = Field(alias="bundleUrl")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/files", response_model=KitFileListResponse)
async def list_kit_files() -> KitFileListResponse:
    """List all available Module Development Kit files."""
    files = [
        KitFileInfo(
            filename=filename,
            description=description,
            download_url=f"/api/v1/module-kit/files/{filename}",
        )
        for filename, description in _KIT_FILES.items()
        if (_KIT_DIR / filename).is_file()
    ]
    return KitFileListResponse(
        files=files,
        bundle_url="/api/v1/module-kit/bundle",
    )


@router.get("/files/{filename}")
async def download_kit_file(filename: str) -> Response:
    """Download a single kit file."""
    if filename not in _KIT_FILES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kit file not found: {filename}",
        )

    file_path = _KIT_DIR / filename
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Kit file missing from filesystem: {filename}",
        )

    content = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix
    content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")

    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/bundle")
async def download_kit_bundle() -> Response:
    """Download all kit files as a single .zip bundle."""
    global _zip_cache  # noqa: PLW0603

    if _zip_cache is None:
        _zip_cache = _build_zip_bundle()

    return Response(
        content=_zip_cache,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="binocular-module-kit.zip"',
        },
    )


def _build_zip_bundle() -> bytes:
    """Build an in-memory zip archive of all kit files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in _KIT_FILES:
            file_path = _KIT_DIR / filename
            if file_path.is_file():
                zf.writestr(
                    f"binocular-module-kit/{filename}",
                    file_path.read_text(encoding="utf-8"),
                )
    return buffer.getvalue()
