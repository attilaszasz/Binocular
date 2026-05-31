from pathlib import Path
from typing import cast

import pytest

from binocular.extensions.contract import ModuleCheckInput
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.runner import ModuleRunner
from binocular.extensions.validator import ModuleValidator
from binocular.scraping.client import ScrapeClient


def validator(tmp_path: Path) -> ModuleValidator:
    return ModuleValidator(ModuleLoader(tmp_path), ModuleRunner())


def write_module(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def proof_input() -> ModuleCheckInput:
    return ModuleCheckInput(device_type="Camera", model="A1", current_version="1.0")


@pytest.mark.asyncio
async def test_validator_skips_runtime_when_static_fails(tmp_path: Path) -> None:
    module_path = write_module(tmp_path / "bad.py", "def nope(:\n")

    result = await validator(tmp_path).validate(module_path, proof_input=proof_input())

    assert result.overall_status == "invalid"
    assert result.static_phase.status == "failed"
    assert result.runtime_phase.status == "skipped"


@pytest.mark.asyncio
async def test_validator_reports_runtime_failure_after_static_pass(tmp_path: Path) -> None:
    module_path = write_module(
        tmp_path / "invalid_runtime.py",
        """
MODULE_METADATA = {"module_id": "test", "display_name": "Test"}

async def check_firmware(input, scrape_client):
    return {"unexpected": True}
""",
    )

    result = await validator(tmp_path).validate(
        module_path,
        proof_input=proof_input(),
        scrape_client=cast(ScrapeClient, object()),
    )

    assert result.static_phase.status == "passed"
    assert result.runtime_phase.status == "failed"
    assert result.overall_status == "invalid"


@pytest.mark.asyncio
async def test_validator_reports_full_pass(tmp_path: Path) -> None:
    module_path = write_module(
        tmp_path / "valid.py",
        """
MODULE_METADATA = {"module_id": "test", "display_name": "Test"}

async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0"}
""",
    )

    result = await validator(tmp_path).validate(
        module_path,
        proof_input=proof_input(),
        scrape_client=cast(ScrapeClient, object()),
    )

    assert result.module_id == "test"
    assert result.static_phase.status == "passed"
    assert result.runtime_phase.status == "passed"
    assert result.overall_status == "valid"