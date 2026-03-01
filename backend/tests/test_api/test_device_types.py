"""Integration tests for device type API endpoints."""

from __future__ import annotations

from httpx import AsyncClient


async def test_device_type_crud_lifecycle(client: AsyncClient) -> None:
    """Create, read, list, update, and delete a device type via API."""

    create_response = await client.post(
        "/api/v1/device-types",
        json={
            "name": "Sony Alpha Bodies",
            "firmware_source_url": "https://example.com/sony",
            "check_frequency_minutes": 120,
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] > 0
    assert created["name"] == "Sony Alpha Bodies"
    assert created["device_count"] == 0

    device_type_id = created["id"]

    get_response = await client.get(f"/api/v1/device-types/{device_type_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == device_type_id

    list_response = await client.get("/api/v1/device-types")
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Sony Alpha Bodies"

    patch_response = await client.patch(
        f"/api/v1/device-types/{device_type_id}",
        json={
            "name": "Sony Alpha Cameras",
            "firmware_source_url": " https://example.com/sony/v2 ",
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["name"] == "Sony Alpha Cameras"
    assert patched["firmware_source_url"] == "https://example.com/sony/v2"

    delete_response = await client.delete(f"/api/v1/device-types/{device_type_id}")
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/device-types/{device_type_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["error_code"] == "NOT_FOUND"


async def test_device_type_duplicate_name_returns_error_envelope(client: AsyncClient) -> None:
    """Creating duplicate device types should return DUPLICATE_NAME envelope."""

    first_response = await client.post(
        "/api/v1/device-types",
        json={
            "name": "Panasonic Lumix",
            "firmware_source_url": "https://example.com/pana",
        },
    )
    assert first_response.status_code == 201

    duplicate_response = await client.post(
        "/api/v1/device-types",
        json={
            "name": "Panasonic Lumix",
            "firmware_source_url": "https://example.com/pana-alt",
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error_code"] == "DUPLICATE_NAME"
    assert duplicate_response.json()["field"] == "name"


async def test_device_type_delete_requires_confirm_cascade_when_children_exist(
    client: AsyncClient,
) -> None:
    """Delete must be blocked without confirm flag when child devices exist."""

    type_response = await client.post(
        "/api/v1/device-types",
        json={"name": "Cascade Type", "firmware_source_url": "https://example.com/cascade"},
    )
    assert type_response.status_code == 201
    device_type_id = int(type_response.json()["id"])

    device_response = await client.post(
        f"/api/v1/device-types/{device_type_id}/devices",
        json={"name": "Child Device", "current_version": "1.0"},
    )
    assert device_response.status_code == 201

    blocked = await client.delete(f"/api/v1/device-types/{device_type_id}")
    assert blocked.status_code == 409
    blocked_payload = blocked.json()
    assert blocked_payload["error_code"] == "CASCADE_BLOCKED"
    assert "1 devices" in blocked_payload["detail"]

    allowed = await client.delete(f"/api/v1/device-types/{device_type_id}?confirm_cascade=true")
    assert allowed.status_code == 204

    missing = await client.get(f"/api/v1/device-types/{device_type_id}")
    assert missing.status_code == 404


async def test_device_type_delete_without_children_does_not_require_flag(
    client: AsyncClient,
) -> None:
    """Delete should succeed without confirm flag when no child devices exist."""

    type_response = await client.post(
        "/api/v1/device-types",
        json={"name": "Empty Type", "firmware_source_url": "https://example.com/empty"},
    )
    assert type_response.status_code == 201
    device_type_id = int(type_response.json()["id"])

    delete_response = await client.delete(f"/api/v1/device-types/{device_type_id}")
    assert delete_response.status_code == 204
