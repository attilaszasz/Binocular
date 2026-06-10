"""Tests for notification configuration and testing API endpoints."""

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from binocular.app import create_app
from binocular.config import Settings


@pytest.fixture
def test_app(tmp_path: Path) -> FastAPI:
    settings = Settings(
        environment="test",
        data_dir=tmp_path,
    )
    return create_app(settings)


@pytest.fixture
def client(test_app: FastAPI) -> Iterator[TestClient]:
    # Use router lifespan to trigger sqlite migration on test db setup
    with TestClient(test_app) as client:
        yield client


def test_list_and_configure_notification_channels(client: TestClient) -> None:
    # 1. Get empty list at start (or default unconfigured)
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Configure SMTP
    payload = {
        "enabled": True,
        "config": {
            "smtpHost": "smtp.test.com",
            "smtpPort": 587,
            "smtpUsername": "user@test.com",
            "smtpPassword": "mySuperSecretPassword",
            "smtpUseTls": True,
            "mailFrom": "alert@binocular.lan",
            "mailTo": "owner@homelab.lan",
        },
    }
    resp = client.put("/api/v1/notifications/smtp", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "smtp"
    assert data["enabled"] is True
    # Verify secret masking
    assert data["config"]["smtpPassword"] == "•"
    assert data["config"]["smtpHost"] == "smtp.test.com"

    # 3. Fetch again and confirm masked config is listed
    resp = client.get("/api/v1/notifications")
    assert resp.status_code == 200
    channels = resp.json()
    assert len(channels) == 1
    assert channels[0]["type"] == "smtp"
    assert channels[0]["config"]["smtpPassword"] == "•"

    # 4. Update without changing secret (sending masked bullet)
    update_payload = {
        "enabled": False,
        "config": {
            "smtpHost": "smtp.test.com",
            "smtpPort": 587,
            "smtpUsername": "user@test.com",
            "smtpPassword": "•",  # Send masked bullet
            "smtpUseTls": True,
            "mailFrom": "alert@binocular.lan",
            "mailTo": "owner@homelab.lan",
        },
    }
    resp = client.put("/api/v1/notifications/smtp", json=update_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["config"]["smtpPassword"] == "•"

    # 5. Invalid port check
    bad_payload = {
        "enabled": True,
        "config": {
            "smtpHost": "smtp.test.com",
            "smtpPort": 9999999,  # Invalid port
            "mailTo": "owner@homelab.lan",
        },
    }
    resp = client.put("/api/v1/notifications/smtp", json=bad_payload)
    assert resp.status_code == 422


@patch("binocular.services.notifications.NotifierService.send_test_notification")
def test_test_notification_endpoints(mock_send_test: AsyncMock, client: TestClient) -> None:
    # Mock NotifierService.send_test_notification to return success
    mock_send_test.return_value = (True, "Test email sent")

    # Stateless test post
    payload = {
        "config": {
            "smtpHost": "smtp.test.com",
            "smtpPort": 25,
            "mailTo": "alert@test.com",
        }
    }
    resp = client.post("/api/v1/notifications/smtp/test", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"status": "success", "detail": "Test email sent"}
    mock_send_test.assert_called_once_with("smtp", payload["config"])
