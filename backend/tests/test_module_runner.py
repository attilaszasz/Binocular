from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import LoadedModule, ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.scraping.client import ScrapeClient


def write_module(path: Path, body: str) -> LoadedModule:
    path.write_text(
        f'MODULE_METADATA = {{"module_id": "test", "display_name": "Test"}}\n{body}',
        encoding="utf-8",
    )
    result = ModuleLoader(path.parent).load(path)
    assert result.loaded_module is not None
    return result.loaded_module


def check_input() -> ModuleCheckInput:
    return ModuleCheckInput(device_type="Camera", model="A1", current_version="1.0")


@pytest.mark.asyncio
async def test_runner_returns_normalized_success(tmp_path: Path) -> None:
    loaded = write_module(
        tmp_path / "valid.py",
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0"}
""",
    )

    result = await ModuleRunner().run(loaded, check_input(), cast(ScrapeClient, object()))

    assert result.status == "success"
    assert result.latest_version == "2.0"


@pytest.mark.asyncio
async def test_runner_contains_exception_and_allows_later_invocation(tmp_path: Path) -> None:
    raising = write_module(
        tmp_path / "raising.py",
        """
async def check_firmware(input, scrape_client):
    raise RuntimeError("boom")
""",
    )
    valid = write_module(
        tmp_path / "valid.py",
        """
async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0"}
""",
    )
    runner = ModuleRunner()

    failed = await runner.run(raising, check_input(), cast(ScrapeClient, object()))
    recovered = await runner.run(valid, check_input(), cast(ScrapeClient, object()))

    assert failed.status == "failed"
    assert failed.diagnostics["error_type"] == "RuntimeError"
    assert recovered.status == "success"


@pytest.mark.asyncio
async def test_runner_reports_timeout(tmp_path: Path) -> None:
    loaded = write_module(
        tmp_path / "slow.py",
        """
import asyncio

async def check_firmware(input, scrape_client):
    await asyncio.sleep(1)
    return {"status": "success", "latest_version": "2.0"}
""",
    )

    result = await ModuleRunner(timeout_seconds=0.01).run(
        loaded,
        check_input(),
        cast(ScrapeClient, object()),
    )

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "timeout"


@pytest.mark.asyncio
async def test_runner_reports_system_exit(tmp_path: Path) -> None:
    loaded = write_module(
        tmp_path / "system_exit.py",
        """
async def check_firmware(input, scrape_client):
    raise SystemExit("stop")
""",
    )

    result = await ModuleRunner().run(loaded, check_input(), cast(ScrapeClient, object()))

    assert result.status == "failed"
    assert result.diagnostics["error_type"] == "SystemExit"
