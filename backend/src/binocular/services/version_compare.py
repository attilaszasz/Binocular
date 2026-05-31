"""Deterministic firmware version comparison."""

import re
from dataclasses import dataclass

_SEGMENT_RE = re.compile(
    r"^v?(?P<body>\d+(?:[._-]\d+)*)(?:[._-]?(?:build|rev)?\d*)?$",
    re.IGNORECASE,
)


class VersionComparisonError(ValueError):
    """Raised when versions cannot be compared without guessing."""


@dataclass(frozen=True)
class VersionComparison:
    """Normalized comparison result for two firmware versions."""

    current: str
    latest: str
    normalized_current: tuple[int, ...]
    normalized_latest: tuple[int, ...]
    is_newer: bool


def compare_versions(current: str, latest: str) -> VersionComparison:
    """Compare two firmware versions using numeric dotted ordering."""

    normalized_current = _normalize(current)
    normalized_latest = _normalize(latest)
    comparable_current, comparable_latest = _pad(normalized_current, normalized_latest)
    return VersionComparison(
        current=current,
        latest=latest,
        normalized_current=normalized_current,
        normalized_latest=normalized_latest,
        is_newer=comparable_latest > comparable_current,
    )


def _normalize(value: str) -> tuple[int, ...]:
    stripped = value.strip()
    if not stripped:
        msg = "Cannot compare an empty version"
        raise VersionComparisonError(msg)
    match = _SEGMENT_RE.match(stripped)
    if match is None:
        msg = f"Cannot compare version: {value}"
        raise VersionComparisonError(msg)
    parts = re.split(r"[._-]", match.group("body"))
    return tuple(int(part) for part in parts)


def _pad(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)), right + (0,) * (width - len(right))
