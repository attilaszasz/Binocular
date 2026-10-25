"""Reject unsafe identities before running any system setup commands."""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("key", ["PUID", "PGID"])
@pytest.mark.parametrize("value", ["0", "00", "000", "000000", "invalid", "-1"])
def test_entrypoint_rejects_unsafe_identity(key: str, value: str) -> None:
    script = Path(__file__).resolve().parents[2] / "entrypoint.sh"
    result = subprocess.run(  # noqa: S603 — fixed repository script, no user input
        ["/bin/sh", str(script), "/usr/bin/id"],
        env={**os.environ, "PUID": "1000", "PGID": "1000", key: value},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "ERROR:" in result.stderr
    assert "Setting up user" not in result.stdout
