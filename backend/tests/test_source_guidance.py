"""Local metadata evidence; golden suites retain authoritative matching tests."""

from pathlib import Path

import pytest

from binocular.extensions.guidance import FIELDS, SourceGuidance
from binocular.extensions.loader import ModuleLoader
from binocular.extensions.validator import ASTValidator
from binocular.services.official_provenance import HISTORICAL_SHIPPED, shipped_path


@pytest.mark.parametrize("name", HISTORICAL_SHIPPED)
def test_eight_official_declarations(name: str) -> None:
    path = shipped_path(name)
    assert path is not None
    result = ModuleLoader(path.parent).load(path)
    assert result.success
    assert ASTValidator().validate(path).passed
    assert result.guidance.display_name
    assert result.guidance.coverage_notes
    assert result.guidance.model_examples
    assert result.guidance.help_url.startswith("https://")
    assert "not exhaustive" in result.guidance.coverage_notes
    if name == "nikon_z_series":
        assert "product_data.xml" in result.source_url
        assert "index.html" in result.guidance.help_url
    if name == "canon_rf_lenses":
        assert "no positive RF-S release verified" in result.guidance.coverage_notes
    if name == "panasonic_lumix_lenses":
        assert result.device_type == "lens"


@pytest.mark.parametrize("constant", FIELDS)
def test_bounds_and_wrong_types(constant: str) -> None:
    _, limit = FIELDS[constant]
    value = ["x" * limit] if constant.endswith("EXAMPLES") else "x" * limit
    SourceGuidance.parse({constant: value})
    for invalid in (
        (["x"] * 11, [""], [42])
        if constant.endswith("EXAMPLES")
        else (42, "x" * (limit + 1))
    ):
        with pytest.raises(ValueError, match=constant):
            SourceGuidance.parse({constant: invalid})


def test_nonliteral_and_runtime_rejected(tmp_path: Path) -> None:
    path = tmp_path / "test.py"
    path.write_text(
        'MODULE_VERSION="1"\nSUPPORTED_DEVICE_TYPE="camera"\n'
        'SOURCE_DISPLAY_NAME=str(12)\ndef check_firmware(a,b,c): return {}'
    )
    assert not ASTValidator().validate(path).passed
    path.write_text(path.read_text().replace("str(12)", "12"))
    assert not ModuleLoader(tmp_path).load(path).success
