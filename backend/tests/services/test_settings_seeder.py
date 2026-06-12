"""Tests for NotificationSettingsSeeder and app lifespan settings seeding."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from binocular.app import create_app
from binocular.config import Settings
from binocular.db.notifications_repository import NotificationsRepository


@pytest.mark.asyncio
async def test_settings_seeder_direct() -> None:
    """Test seeding configurations directly via NotificationSettingsSeeder."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user@gmail.com",
            smtp_password="mypassword",  # noqa: S106
            smtp_from="user@gmail.com",
            smtp_to="user@gmail.com",
            gotify_url="https://gotify.example.com",
            gotify_token="mygotifytoken",  # noqa: S106
        )

        app = create_app(settings=settings)
        async with app.router.lifespan_context(app):
            db = app.state.db
            repo = NotificationsRepository(db)

            # Retrieve seeded Email setting
            email_row = await repo.get_by_type("email")
            assert email_row is not None
            assert bool(email_row["enabled"]) is True
            email_config = json.loads(email_row["config"])
            assert email_config["smtp_host"] == "smtp.gmail.com"
            assert email_config["smtp_port"] == 587
            assert email_config["smtp_use_tls"] is True
            assert email_config["smtp_user"] == "user@gmail.com"
            assert email_config["smtp_pass"] == "mypassword"  # noqa: S105
            assert email_config["from_email"] == "user@gmail.com"
            assert email_config["to_email"] == "user@gmail.com"

            # Retrieve seeded Gotify setting
            gotify_row = await repo.get_by_type("gotify")
            assert gotify_row is not None
            assert bool(gotify_row["enabled"]) is True
            gotify_config = json.loads(gotify_row["config"])
            assert gotify_config["server_url"] == "https://gotify.example.com"
            assert gotify_config["app_token"] == "mygotifytoken"  # noqa: S105


@pytest.mark.asyncio
async def test_settings_seeder_partial_seeding() -> None:
    """Test that seeding is skipped for channels where env vars are not set."""
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(
            data_dir=Path(td),
            modules_dir=Path(td) / "modules",
            seed_modules=False,
            # SMTP defined, Gotify omitted
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user@gmail.com",
            smtp_password="mypassword",  # noqa: S106
            smtp_from="user@gmail.com",
            smtp_to="user@gmail.com",
            gotify_url=None,
            gotify_token=None,
        )

        app = create_app(settings=settings)
        async with app.router.lifespan_context(app):
            db = app.state.db
            repo = NotificationsRepository(db)

            # Email should be seeded
            email_row = await repo.get_by_type("email")
            assert email_row is not None
            assert bool(email_row["enabled"]) is True

            # Gotify should NOT be seeded
            gotify_row = await repo.get_by_type("gotify")
            assert gotify_row is None
