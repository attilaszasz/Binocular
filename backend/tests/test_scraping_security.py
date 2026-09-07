"""Static security acceptance checks for official extension transports."""

from __future__ import annotations

import ast
from pathlib import Path


def test_official_modules_have_no_alternate_network_transport() -> None:
    root = Path(__file__).parents[1] / "src" / "binocular" / "official_modules"
    forbidden = {"httpx", "requests", "socket", "urllib.request", "subprocess"}
    findings: list[str] = []
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {node.module or ""}
            else:
                continue
            if names & forbidden:
                findings.append(f"{path.name}:{node.lineno}")
    assert findings == []
