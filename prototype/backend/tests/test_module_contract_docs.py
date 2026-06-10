from pathlib import Path


def test_extension_docs_state_unsandboxed_trust_boundary() -> None:
    readme = Path("src/binocular/extensions/README.md").read_text(encoding="utf-8")

    assert "not sandboxed" in readme
    assert "same application privileges" in readme
    assert "must not be described as one" in readme
