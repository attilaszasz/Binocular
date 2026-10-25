"""Host-owned proof of shipped bytes; names and author claims are not proof."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

# Captured from git b1b8b99 before guidance edits (2026-10-07).
HISTORICAL_SHIPPED = {
    "sony_alpha": (
        "1.0.0",
        "ee30f81150e86c4b437cdb8f756100d950c8fe49fc96e6b975776c353ebaf319",
    ),
    "panasonic_lumix": (
        "1.0.0",
        "b3b5c597c8b275ba4e147f037cafc05ab497d68a01baf39e631d8560bbaf50ee",
    ),
    "panasonic_lumix_lenses": (
        "1.0.0",
        "abe5bbaddebdcad21719596281ff81f163833e704ae8e2616f6977189ced74fc",
    ),
    "godox_flashes": (
        "1.0.0",
        "10842d170b7e61fd98877ed4a01d181735ceecc5962d6cf4c306077190f74764",
    ),
    "viltrox_lenses": (
        "1.0.0",
        "0fc6c8c5c5d890036193ae95d0fdb505e5d765d7402d34beb957098df2503e84",
    ),
    "nikon_z_series": (
        "1.0.0",
        "de58dd4c7b70098e0d2c9dbb0a6e4c62844a02a730af3a5af7879617b7acc644",
    ),
    "canon_rf_cameras": (
        "1.0.0",
        "4a0b74f67e87ea58720bdb8eee7ccbedf666a8e2c7bd4b485d9bfaa28b6bbcc3",
    ),
    "canon_rf_lenses": (
        "1.0.0",
        "2a7fb541c1e19e11ced22b18d4b46aaf93245851a68c5a8aadbf1b2386b92560",
    ),
}


def content_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def shipped_path(name: str) -> Path | None:
    if name not in HISTORICAL_SHIPPED:
        return None
    return Path(__file__).parent.parent / "official_modules" / f"{name}.py"


def guidance_provenance(row: dict[str, Any]) -> str:
    if row.get("registration_origin") == "custom":
        return "custom"
    bundled = shipped_path(row["name"])
    if bundled and row.get("registration_origin") == "bundled":
        digest = content_hash(Path(row.get("file_path") or ""))
        if digest and digest == row.get("official_content_hash") == content_hash(
            bundled
        ):
            return "verified_official"
    return "legacy"
