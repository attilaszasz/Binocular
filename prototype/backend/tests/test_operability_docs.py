from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compose_declares_single_port_and_volumes() -> None:
    compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")

    assert "8000:8000" in compose
    assert "/app/data" in compose
    assert "/app/modules" in compose
    assert "env_file" in compose


def test_env_example_documents_auth_and_secret_defaults() -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "BINOCULAR_AUTH_ENABLED=false" in env_example
    assert "BINOCULAR_AUTH_USERNAME=" in env_example
    assert "BINOCULAR_AUTH_PASSWORD_FILE=" in env_example
    assert "trusted lan" in env_example.lower()


def test_readme_documents_basic_auth_boundary() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "basic auth" in readme
    assert "not a substitute" in readme
