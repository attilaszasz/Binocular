from pathlib import Path

from binocular.extensions.loader import ModuleLoader


def write_module(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    return path


def test_module_loader_loads_valid_contract(tmp_path: Path) -> None:
    module_path = write_module(
        tmp_path / "valid_module.py",
        """
MODULE_METADATA = {"module_id": "sony-alpha", "display_name": "Sony Alpha"}

async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.0"}
""",
    )

    result = ModuleLoader(tmp_path).load(module_path)

    assert result.success is True
    assert result.loaded_module is not None
    assert result.loaded_module.metadata.module_id == "sony-alpha"


def test_module_loader_reports_invalid_syntax(tmp_path: Path) -> None:
    module_path = write_module(tmp_path / "bad_syntax.py", "def nope(:\n")

    result = ModuleLoader(tmp_path).load(module_path)

    assert result.success is False
    assert result.failure is not None
    assert result.failure.error_type == "syntax_error"


def test_module_loader_reports_missing_entrypoint(tmp_path: Path) -> None:
    module_path = write_module(
        tmp_path / "missing_entrypoint.py",
        'MODULE_METADATA = {"module_id": "sony-alpha", "display_name": "Sony Alpha"}\n',
    )

    result = ModuleLoader(tmp_path).load(module_path)

    assert result.success is False
    assert result.failure is not None
    assert result.failure.error_type == "missing_entrypoint"
