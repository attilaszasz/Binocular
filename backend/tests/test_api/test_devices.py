"""Integration tests for device API endpoints."""

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


async def test_device_crud_with_enriched_response(client: AsyncClient) -> None:
    """Device CRUD should include derived status and parent type name enrichment."""

    device_type_id = await _create_device_type(client, "Sony Alpha Bodies")

    create_response = await client.post(
        f"/api/v1/device-types/{device_type_id}/devices",
        json={
            "name": "Sony A7IV",
            "current_version": "3.01",
            "notes": " Primary body ",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] > 0
    assert created["device_type_id"] == device_type_id
    assert created["device_type_name"] == "Sony Alpha Bodies"
    assert created["status"] == "never_checked"
    assert created["notes"] == "Primary body"

    device_id = int(created["id"])

    get_response = await client.get(f"/api/v1/devices/{device_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Sony A7IV"

    update_response = await client.patch(
        f"/api/v1/devices/{device_id}",
        json={"notes": " Favorite for travel "},
    )
    assert update_response.status_code == 200
    assert update_response.json()["notes"] == "Favorite for travel"

    list_response = await client.get("/api/v1/devices")
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["device_type_name"] == "Sony Alpha Bodies"

    delete_response = await client.delete(f"/api/v1/devices/{device_id}")
    assert delete_response.status_code == 204

    missing_response = await client.get(f"/api/v1/devices/{device_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["error_code"] == "NOT_FOUND"


async def test_duplicate_name_within_type_rejected_cross_type_allowed(client: AsyncClient) -> None:
    """Duplicate names should be blocked within one type but allowed across types."""

    sony_type_id = await _create_device_type(client, "Sony Type")
    pana_type_id = await _create_device_type(client, "Panasonic Type")

    first = await client.post(
        f"/api/v1/device-types/{sony_type_id}/devices",
        json={"name": "A7IV", "current_version": "1.0"},
    )
    assert first.status_code == 201

    duplicate_same_type = await client.post(
        f"/api/v1/device-types/{sony_type_id}/devices",
        json={"name": "A7IV", "current_version": "1.1"},
    )
    assert duplicate_same_type.status_code == 409
    assert duplicate_same_type.json()["error_code"] == "DUPLICATE_NAME"

    duplicate_other_type = await client.post(
        f"/api/v1/device-types/{pana_type_id}/devices",
        json={"name": "A7IV", "current_version": "2.0"},
    )
    assert duplicate_other_type.status_code == 201


async def test_device_list_filtering_and_sorting(client: AsyncClient, db_path: str) -> None:
    """List endpoint should support type/status filtering and deterministic sorting."""

    sony_type_id = await _create_device_type(client, "Sony Sort")
    pana_type_id = await _create_device_type(client, "Panasonic Sort")

    create_alpha = await client.post(
        f"/api/v1/device-types/{sony_type_id}/devices",
        json={"name": "Alpha", "current_version": "1.0"},
    )
    create_zeta = await client.post(
        f"/api/v1/device-types/{sony_type_id}/devices",
        json={"name": "Zeta", "current_version": "1.0"},
    )
    create_beta = await client.post(
        f"/api/v1/device-types/{pana_type_id}/devices",
        json={"name": "Beta", "current_version": "1.0"},
    )
    assert create_alpha.status_code == 201
    assert create_zeta.status_code == 201
    assert create_beta.status_code == 201

    alpha_id = int(create_alpha.json()["id"])
    zeta_id = int(create_zeta.json()["id"])

    repo = DeviceRepo(db_path)
    await repo.update_latest_version(alpha_id, "1.0", datetime.now(UTC) - timedelta(minutes=1))
    await repo.update_latest_version(zeta_id, "2.0", datetime.now(UTC) - timedelta(minutes=2))

    filtered_type = await client.get(f"/api/v1/devices?device_type_id={sony_type_id}")
    assert filtered_type.status_code == 200
    filtered_type_names = [row["name"] for row in filtered_type.json()]
    assert filtered_type_names == ["Alpha", "Zeta"]

    filtered_status = await client.get("/api/v1/devices?status=update_available")
    assert filtered_status.status_code == 200
    filtered_status_names = [row["name"] for row in filtered_status.json()]
    assert filtered_status_names == ["Zeta"]

    sort_name = await client.get("/api/v1/devices?sort=name")
    assert sort_name.status_code == 200
    assert [row["name"] for row in sort_name.json()] == ["Alpha", "Beta", "Zeta"]

    sort_name_desc = await client.get("/api/v1/devices?sort=-name")
    assert sort_name_desc.status_code == 200
    assert [row["name"] for row in sort_name_desc.json()] == ["Zeta", "Beta", "Alpha"]

    sort_checked_desc = await client.get("/api/v1/devices?sort=-last_checked_at")
    assert sort_checked_desc.status_code == 200
    assert [row["name"] for row in sort_checked_desc.json()] == ["Alpha", "Zeta", "Beta"]

    invalid_sort = await client.get("/api/v1/devices?sort=created_at")
    assert invalid_sort.status_code == 422
    assert invalid_sort.json()["error_code"] == "VALIDATION_ERROR"
