"""Responsive HTML email renderer using Jinja2 templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class EmailRenderer:
    """Renders responsive HTML emails using Jinja2 templates."""

    def __init__(self, templates_dir: Path | None = None) -> None:
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=True,
        )

    def render_update_alert(
        self,
        device_name: str,
        model: str,
        module_name: str,
        current_version: str,
        latest_version: str,
    ) -> str:
        """Render the new firmware update alert HTML mail."""
        template = self._env.get_template("email.html")
        return template.render(
            device_name=device_name,
            model=model,
            module_name=module_name,
            current_version=current_version,
            latest_version=latest_version,
        )
