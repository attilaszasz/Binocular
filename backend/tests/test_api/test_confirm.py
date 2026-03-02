"""Integration tests for confirm action endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from backend.src.repositories.device_repo import DeviceRepo


async def _create_device_type(client: AsyncClient, name: str) -> int:
    response = await client.post(
        "/api/v1/device-types",
        json={
            "name": name,
            "firmware_source_url": f"https://example.com/{name.lower().replace(' ', '-')}",
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def _create_device(
    client: AsyncClient,
    device_type_id: int,
    name: str,
    version: str,
    model: str | None = None,
) -> int:
    payload = {"name": name, "current_version": version}
    if model is not None:
        payload["model"] = model

    response = await client.post(
        f"/api/v1/device-types/{device_type_id}/devices",
        json=payload,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


async def test_single_device_confirm_happy_path_and_idempotency(
    client: AsyncClient,
    db_path: str,
) -> None:
    """Confirm should sync versions and remain safe to repeat."""

    device_type_id = await _create_device_type(client, "Sony Confirm")
    device_id = await _create_device(client, device_type_id, "A7IV", "2.00", model="ILCE-7M4")

    repo = DeviceRepo(db_path)
    await repo.update_latest_version(device_id, "3.01", datetime.now(UTC))

    confirm_response = await client.post(f"/api/v1/devices/{device_id}/confirm")
    assert confirm_response.status_code == 200
    first_payload = confirm_response.json()
    assert first_payload["current_version"] == "3.01"
    assert first_payload["latest_seen_version"] == "3.01"
    assert first_payload["status"] == "up_to_date"
    assert first_payload["model"] == "ILCE-7M4"

    second_response = await client.post(f"/api/v1/devices/{device_id}/confirm")
    assert second_response.status_code == 200
    second_payload = second_response.json()
    assert second_payload["current_version"] == "3.01"
    assert second_payload["status"] == "up_to_date"
    assert second_payload["model"] == "ILCE-7M4"


async def test_single_device_confirm_rejects_never_checked(client: AsyncClient) -> None:
    """Confirm should reject devices without latest_seen_version."""

    device_type_id = await _create_device_type(client, "Never Checked")
    device_id = await _create_device(client, device_type_id, "Z8", "1.0")

    response = await client.post(f"/api/v1/devices/{device_id}/confirm")
    assert response.status_code == 409
    assert response.json()["error_code"] == "NO_LATEST_VERSION"


async def test_bulk_confirm_mixed_states_filter_and_idempotency(
    client: AsyncClient,
    db_path: str,
) -> None:
    """Bulk confirm should process pending updates, support filtering, and be idempotent."""

    sony_type_id = await _create_device_type(client, "Bulk Sony")
    pana_type_id = await _create_device_type(client, "Bulk Panasonic")

    sony_pending_id = await _create_device(client, sony_type_id, "Sony Pending", "1.0")
    sony_up_to_date_id = await _create_device(client, sony_type_id, "Sony Current", "2.0")
    await _create_device(client, sony_type_id, "Sony Never", "1.0")
    pana_pending_id = await _create_device(client, pana_type_id, "Pana Pending", "5.0")

    repo = DeviceRepo(db_path)
    now = datetime.now(UTC)
    await repo.update_latest_version(sony_pending_id, "2.0", now)
    await repo.update_latest_version(sony_up_to_date_id, "2.0", now - timedelta(minutes=1))
    await repo.update_latest_version(pana_pending_id, "6.0", now - timedelta(minutes=2))

    filtered_bulk = await client.post(f"/api/v1/devices/confirm-all?device_type_id={sony_type_id}")
    assert filtered_bulk.status_code == 200
    filtered_payload = filtered_bulk.json()
    assert filtered_payload["confirmed"] == 1
    assert filtered_payload["skipped"] == 2
    assert filtered_payload["errors"] == 0
    assert filtered_payload["details"] == []

    pana_after_filtered = await client.get(f"/api/v1/devices/{pana_pending_id}")
    assert pana_after_filtered.status_code == 200
    assert pana_after_filtered.json()["status"] == "update_available"

    global_bulk = await client.post("/api/v1/devices/confirm-all")
    assert global_bulk.status_code == 200
    global_payload = global_bulk.json()
    assert global_payload["confirmed"] == 1
    assert global_payload["skipped"] == 3
    assert global_payload["errors"] == 0

    second_global = await client.post("/api/v1/devices/confirm-all")
    assert second_global.status_code == 200
    second_payload = second_global.json()
    assert second_payload["confirmed"] == 0
    assert second_payload["skipped"] == 4
    assert second_payload["errors"] == 0
