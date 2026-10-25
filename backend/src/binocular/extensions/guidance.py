"""Bounded, optional V1 author guidance. No network or executable parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

FIELDS = {
    "SOURCE_DISPLAY_NAME": ("display_name", 120),
    "SOURCE_COVERAGE_NOTES": ("coverage_notes", 1000),
    "SOURCE_MODEL_EXAMPLES": ("model_examples", 120),
    "SOURCE_HELP_URL": ("help_url", 2048),
}


def safe_source_url(value: str) -> str:
    """Only absolute HTTP(S), without credentials or control characters."""
    if any(ord(c) < 33 or ord(c) == 127 for c in value):
        return ""
    try:
        url = urlsplit(value)
        if url.scheme.lower() not in {"http", "https"} or not url.hostname:
            return ""
        if url.username is not None or url.password is not None:
            return ""
        _ = url.port
    except ValueError:
        return ""
    return value


@dataclass(frozen=True, slots=True)
class SourceGuidance:
    display_name: str = ""
    coverage_notes: str = ""
    model_examples: tuple[str, ...] = ()
    help_url: str = ""

    @classmethod
    def parse(cls, declarations: dict[str, Any]) -> SourceGuidance:
        values: dict[str, Any] = {}
        for constant, (field, limit) in FIELDS.items():
            value = declarations.get(constant, () if field == "model_examples" else "")
            if field == "model_examples":
                if not isinstance(value, (list, tuple)) or len(value) > 10:
                    raise ValueError(
                        f"{constant}: use a list/tuple of at most 10 strings"
                    )
                if any(
                    not isinstance(x, str) or not x.strip() or len(x) > limit
                    for x in value
                ):
                    raise ValueError(
                        f"{constant}: each example must be nonblank text "
                        f"of at most {limit} characters"
                    )
                values[field] = tuple(value)
            else:
                if not isinstance(value, str) or len(value) > limit:
                    raise ValueError(
                        f"{constant}: use text of at most {limit} characters"
                    )
                values[field] = safe_source_url(value) if field == "help_url" else value
        return cls(**values)

    def persistence(self) -> dict[str, str]:
        return {
            "display_name": self.display_name,
            "coverage_notes": self.coverage_notes,
            "model_examples": json.dumps(self.model_examples),
            "help_url": self.help_url,
        }

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> SourceGuidance:
        try:
            examples = json.loads(row.get("model_examples", "[]"))
            return cls.parse(
                {
                    constant: examples
                    if field == "model_examples"
                    else row.get(field, "")
                    for constant, (field, _) in FIELDS.items()
                }
            )
        except (ValueError, TypeError):
            return cls()


def readable_name(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").strip().title()
