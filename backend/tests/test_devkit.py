from pathlib import Path
import json
import pytest

from binocular.extensions.devkit import DevKitCLI, mock_handler


def write_module(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    return path


def test_devkit_parse_extras() -> None:
    cli = DevKitCLI()
    res = cli._parse_extras("foo=bar,baz=qux")
    assert res == {"foo": "bar", "baz": "qux"}

    res_empty = cli._parse_extras(None)
    assert res_empty == {}


def test_devkit_check_valid_module(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "valid_module.py",
        """
MODULE_METADATA = {"module_id": "test-id", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "1.0.0"}
""",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli(["check", str(module_path)])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "✓ Static contract validation: PASSED" in captured.out
    assert "Module ID:    test-id" in captured.out


def test_devkit_check_valid_module_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "valid_module.py",
        """
MODULE_METADATA = {"module_id": "test-id", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "1.0.0"}
""",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli(["check", str(module_path), "--json"])
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["status"] == "passed"
    assert data["module_id"] == "test-id"


def test_devkit_check_invalid_syntax(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "bad_syntax.py",
        "def broken(:\n",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli(["check", str(module_path)])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "✗ Static contract validation: FAILED" in captured.err
    assert "syntax_error" in captured.err


def test_devkit_check_invalid_syntax_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "bad_syntax.py",
        "def broken(:\n",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli(["check", str(module_path), "--json"])
    assert exit_code == 1

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["status"] == "failed"
    assert data["error_type"] == "syntax_error"


def test_devkit_run_valid_module_mock(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "valid_module.py",
        """
MODULE_METADATA = {"module_id": "test-id", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    # Fetch from local mock transport
    res = await scrape_client.fetch(input.source_url)
    assert "Latest Version:</span>" in res.text
    assert "2.5.0" in res.text
    return {"status": "success", "latest_version": "2.5.0"}
""",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli([
        "run",
        str(module_path),
        "--device-type", "camera",
        "--model", "Alpha 7",
        "--current-version", "1.0.0",
    ])
    assert exit_code == 0

    captured = capsys.readouterr()
    assert "✓ Module Execution: SUCCESS" in captured.out
    assert "Latest Version: 2.5.0" in captured.out


def test_devkit_run_valid_module_mock_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "valid_module.py",
        """
MODULE_METADATA = {"module_id": "test-id", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    return {"status": "success", "latest_version": "2.5.0", "detail": "parsed correctly"}
""",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli([
        "run",
        str(module_path),
        "--device-type", "camera",
        "--model", "Alpha 7",
        "--current-version", "1.0.0",
        "--json",
    ])
    assert exit_code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["status"] == "success"
    assert data["latest_version"] == "2.5.0"
    assert data["detail"] == "parsed correctly"


def test_devkit_run_failed_execution(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    module_path = write_module(
        tmp_path / "failing_module.py",
        """
MODULE_METADATA = {"module_id": "test-id", "display_name": "Test Module"}

async def check_firmware(input, scrape_client):
    raise ValueError("Something went terribly wrong in scraper")
""",
    )

    cli = DevKitCLI()
    exit_code = cli.run_cli([
        "run",
        str(module_path),
        "--device-type", "camera",
        "--model", "Alpha 7",
        "--current-version", "1.0.0",
    ])
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "✗ Module Execution: FAILED" in captured.err
    assert "ValueError" in captured.err
    assert "Something went terribly wrong in scraper" in captured.err

