"""Tests for the ModuleLoader."""

from __future__ import annotations

from pathlib import Path

from binocular.extensions.loader import ModuleLoader

FIXTURES = Path(__file__).parent / "fixtures"


class TestModuleLoaderDiscover:
    """Discovery tests."""

    def test_discover_finds_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "mod_a.py").write_text("# module a")
        (tmp_path / "mod_b.py").write_text("# module b")
        (tmp_path / "readme.txt").write_text("not a module")
        (tmp_path / "subdir").mkdir()

        loader = ModuleLoader(tmp_path)
        paths = loader.discover()
        assert len(paths) == 2
        assert all(p.suffix == ".py" for p in paths)

    def test_discover_missing_dir(self, tmp_path: Path) -> None:
        loader = ModuleLoader(tmp_path / "nonexistent")
        paths = loader.discover()
        assert paths == []


class TestModuleLoaderLoad:
    """Loading and conformance tests."""

    def test_load_valid_module(self) -> None:
        loader = ModuleLoader(FIXTURES)
        result = loader.load(FIXTURES / "valid_module.py")
        assert result.success is True
        assert result.module is not None
        assert result.module_name == "valid_module"
        assert result.device_type == "camera"
        assert result.version == "1.0.0"
        assert result.errors == []

    def test_load_missing_function(self) -> None:
        loader = ModuleLoader(FIXTURES)
        result = loader.load(FIXTURES / "missing_function.py")
        assert result.success is False
        assert any("check_firmware" in e.message for e in result.errors)

    def test_load_missing_constants(self) -> None:
        loader = ModuleLoader(FIXTURES)
        result = loader.load(FIXTURES / "missing_constant.py")
        assert result.success is False
        assert any("MODULE_VERSION" in e.message for e in result.errors)
        assert any("SUPPORTED_DEVICE_TYPE" in e.message for e in result.errors)

    def test_load_syntax_error(self) -> None:
        loader = ModuleLoader(FIXTURES)
        result = loader.load(FIXTURES / "syntax_error.py")
        assert result.success is False
        assert any("syntax" in e.attribute.lower() for e in result.errors)

    def test_does_not_pollute_sys_modules(self) -> None:
        import sys

        loader = ModuleLoader(FIXTURES)
        loader.load(FIXTURES / "valid_module.py")
        assert "valid_module" not in sys.modules


class TestModuleLoaderLoadAll:
    """Batch loading tests."""

    def test_load_all(self, tmp_path: Path) -> None:
        (tmp_path / "good.py").write_text(
            'MODULE_VERSION = "1.0"\n'
            'SUPPORTED_DEVICE_TYPE = "router"\n'
            "def check_firmware(url, model, http_client):\n"
            '    return {"latest_version": "1.0"}\n'
        )
        (tmp_path / "bad.py").write_text("# missing everything\n")

        loader = ModuleLoader(tmp_path)
        results = loader.load_all()
        assert len(results) == 2
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) == 1
        assert len(failures) == 1
