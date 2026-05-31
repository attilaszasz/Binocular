import pytest

from binocular.services.version_compare import VersionComparisonError, compare_versions


@pytest.mark.parametrize(
    ("current", "latest", "is_newer"),
    [
        ("1.0", "1.1", True),
        ("1.10", "1.2", False),
        ("v2.0.0", "2.0.1", True),
        ("02", "2", False),
        ("1.0.0", "1.0", False),
        ("3.0", "2.9", False),
    ],
)
def test_compare_versions_orders_common_firmware_versions(
    current: str,
    latest: str,
    is_newer: bool,
) -> None:
    result = compare_versions(current, latest)

    assert result.is_newer is is_newer
    assert result.current == current
    assert result.latest == latest


@pytest.mark.parametrize("current,latest", [("", "1.0"), ("1.0", ""), ("alpha", "1.0")])
def test_compare_versions_rejects_unsafe_values(current: str, latest: str) -> None:
    with pytest.raises(VersionComparisonError):
        compare_versions(current, latest)
