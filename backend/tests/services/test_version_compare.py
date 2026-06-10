"""Tests for VersionCompare utility."""

from __future__ import annotations

import pytest

from binocular.services.version_compare import VersionCompare


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("1.0.0", "1.0.1", True),
        ("1.0.1", "1.0.0", False),
        ("1.0.0", "1.0.0", False),
        ("v1.2", "v1.3", True),
        ("version-1.2.3", "v1.2.4", True),
        ("20260601-01", "20260610-01", True),
        ("20260610-01", "20260601-01", False),
        ("1.1a", "1.1b", True),
        ("1.1b", "1.1a", False),
        ("1.0", "1.0-alpha", False),  # alpha is pre-release, so release 1.0 is newer
        ("1.0-alpha", "1.0", True),
        ("1.0-beta", "1.0-rc", True),
        ("1.0", "1.0a", True),  # suffix a is update, so 1.0a is newer
        ("1.0a", "1.0", False),
        ("1", "2", True),
        ("foo", "bar", False),  # fallback to string compare, 'bar' < 'foo'
        ("bar", "foo", True),   # fallback to string compare, 'foo' > 'bar'
    ],
)
def test_version_compare_is_newer(current: str, latest: str, expected: bool) -> None:
    assert VersionCompare.is_newer(current, latest) is expected
