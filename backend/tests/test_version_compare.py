"""Tests for semver comparison and string fallback behavior."""

from __future__ import annotations

from backend.src.utils.version_compare import derive_device_status, is_update_available


def test_semver_ordered_pairs() -> None:
    """Semver parsing compares numeric version ordering correctly."""

    assert is_update_available("2.0.0", "3.0.0") is True
    assert is_update_available("3.0.0", "2.0.0") is False


def test_fallback_to_string_inequality_on_parse_failure() -> None:
    """Non-semver values use string inequality fallback."""

    assert is_update_available("FW_2024A", "FW_2025B") is True
    assert is_update_available("release-x", "release-x") is False


def test_edge_cases_dates_letters_and_hashes() -> None:
    """Edge version strings do not raise and still produce deterministic output."""

    assert is_update_available("2024-01-01", "2024-01-02") is True
    assert is_update_available("A1", "A1") is False
    assert is_update_available("build#abc", "build#def") is True


def test_derive_device_status() -> None:
    """Status derivation distinguishes never checked, up to date, and update available."""

    assert derive_device_status("1.0.0", None) == "never_checked"
    assert derive_device_status("1.0.0", "1.0.0") == "up_to_date"
    assert derive_device_status("1.0.0", "1.1.0") == "update_available"
