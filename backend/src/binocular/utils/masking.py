"""Masking utilities for sensitive settings."""


def mask_secret(val: str | None) -> str | None:
    """Mask a sensitive value (password/token) with a bullet character if populated."""

    if val is None:
        return None
    if not val:
        return ""
    return "•"
