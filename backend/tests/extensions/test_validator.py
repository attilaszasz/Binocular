"""Tests for the two-phase validation pipeline."""

from __future__ import annotations

from pathlib import Path

from binocular.extensions.loader import ModuleLoader
from binocular.extensions.validator import (
    ASTValidator,
    RuntimeValidator,
    validate_module,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestASTValidator:
    """Phase 1: AST static analysis tests."""

    def test_valid_module_passes(self) -> None:
        validator = ASTValidator()
        result = validator.validate(FIXTURES / "valid_module.py")
        assert result.passed is True
        assert result.phase == "ast"
        assert all(c.passed for c in result.checks)

    def test_missing_function_fails(self) -> None:
        validator = ASTValidator()
        result = validator.validate(FIXTURES / "missing_function.py")
        assert result.passed is False
        failing = [c for c in result.checks if not c.passed]
        assert any("check_firmware" in c.message for c in failing)

    def test_missing_constants_fails(self) -> None:
        validator = ASTValidator()
        result = validator.validate(FIXTURES / "missing_constant.py")
        assert result.passed is False
        failing = [c for c in result.checks if not c.passed]
        assert any("MODULE_VERSION" in c.message for c in failing)
        assert any("SUPPORTED_DEVICE_TYPE" in c.message for c in failing)

    def test_syntax_error_fails(self) -> None:
        validator = ASTValidator()
        result = validator.validate(FIXTURES / "syntax_error.py")
        assert result.passed is False
        assert any(c.name == "syntax" for c in result.checks)
        syntax_check = next(c for c in result.checks if c.name == "syntax")
        assert syntax_check.line is not None

    def test_fix_suggestions_present(self) -> None:
        validator = ASTValidator()
        result = validator.validate(FIXTURES / "missing_function.py")
        failing = [c for c in result.checks if not c.passed]
        assert all(c.fix_suggestion is not None for c in failing)

    def test_wrong_signature_param_count(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad_sig.py"
        bad.write_text(
            'MODULE_VERSION = "1.0"\n'
            'SUPPORTED_DEVICE_TYPE = "camera"\n'
            "def check_firmware(url):\n"
            "    pass\n"
        )
        validator = ASTValidator()
        result = validator.validate(bad)
        assert result.passed is False
        failing = [c for c in result.checks if not c.passed]
        assert any(
            "parameter" in c.message.lower() for c in failing
        )


class TestRuntimeValidator:
    """Phase 2: Runtime proof tests."""

    def test_valid_module_passes(self) -> None:
        loader = ModuleLoader(FIXTURES)
        load_result = loader.load(FIXTURES / "valid_module.py")
        assert load_result.success
        assert load_result.module is not None

        validator = RuntimeValidator()
        result = validator.validate(load_result.module)
        assert result.passed is True
        assert result.phase == "runtime"

    def test_raising_module_fails(self) -> None:
        loader = ModuleLoader(FIXTURES)
        load_result = loader.load(FIXTURES / "raising_module.py")
        assert load_result.success
        assert load_result.module is not None

        validator = RuntimeValidator()
        result = validator.validate(load_result.module)
        assert result.passed is False
        assert any(c.name == "execution" and not c.passed for c in result.checks)

    def test_return_type_validation(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad_return.py"
        bad.write_text(
            'MODULE_VERSION = "1.0"\n'
            'SUPPORTED_DEVICE_TYPE = "camera"\n'
            "def check_firmware(url, model, http_client):\n"
            '    return "not a dict"\n'
        )
        loader = ModuleLoader(tmp_path)
        load_result = loader.load(bad)
        assert load_result.success
        assert load_result.module is not None

        validator = RuntimeValidator()
        result = validator.validate(load_result.module)
        assert result.passed is False
        assert any("return_type" in c.name for c in result.checks if not c.passed)


class TestValidateModule:
    """Combined validation pipeline tests."""

    def test_phase1_only(self) -> None:
        result = validate_module(FIXTURES / "valid_module.py")
        assert result.valid is True
        assert len(result.phases) == 1
        assert result.phases[0].phase == "ast"

    def test_phase1_and_phase2(self) -> None:
        loader = ModuleLoader(FIXTURES)
        load_result = loader.load(FIXTURES / "valid_module.py")
        assert load_result.success
        assert load_result.module is not None

        result = validate_module(
            FIXTURES / "valid_module.py",
            loaded_module=load_result.module,
            run_phase2=True,
        )
        assert result.valid is True
        assert len(result.phases) == 2

    def test_phase2_skipped_on_phase1_failure(self) -> None:
        result = validate_module(
            FIXTURES / "missing_function.py",
            run_phase2=True,
        )
        assert result.valid is False
        assert len(result.phases) == 1  # Phase 2 skipped

    def test_source_path_recorded(self) -> None:
        result = validate_module(FIXTURES / "valid_module.py")
        assert "valid_module.py" in result.source_path
