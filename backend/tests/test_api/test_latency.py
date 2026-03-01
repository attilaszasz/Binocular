"""Latency benchmarks for Inventory API endpoints (SC-008)."""

from __future__ import annotations

from datetime import UTC, datetime
from math import ceil
from time import perf_counter

from httpx import AsyncClient

from backend.src.repositories.device_repo import DeviceRepo


def _p95(samples: list[float]) -> float:
    if not samples:
        return 0.0
    sorted_samples = sorted(samples)
    index = max(0, ceil(len(sorted_samples) * 0.95) - 1)
    return sorted_samples[index]


async def test_api_latency_thresholds(client: AsyncClient, db_path: str) -> None:
    """p95 should remain under SC-008 thresholds for expected V1 load."""

    type_response = await client.post(
        "/api/v1/device-types",
        json={"name": "Latency Type", "firmware_source_url": "https://example.com/latency"},
    )
    assert type_response.status_code == 201
    device_type_id = int(type_response.json()["id"])

    first_device_id: int | None = None
    for index in range(120):
        create_response = await client.post(
            f"/api/v1/device-types/{device_type_id}/devices",
            json={"name": f"Latency Device {index:03d}", "current_version": "1.0"},
        )
        assert create_response.status_code == 201
        if first_device_id is None:
            first_device_id = int(create_response.json()["id"])

    assert first_device_id is not None

    repo = DeviceRepo(db_path)
    await repo.update_latest_version(first_device_id, "1.1", datetime.now(UTC))

    single_entity_samples: list[float] = []
    for iteration in range(30):
        start = perf_counter()
        get_response = await client.get(f"/api/v1/devices/{first_device_id}")
        elapsed = perf_counter() - start
        assert get_response.status_code == 200
        single_entity_samples.append(elapsed)

        start = perf_counter()
        patch_response = await client.patch(
            f"/api/v1/devices/{first_device_id}",
            json={"notes": f"latency-note-{iteration}"},
        )
        elapsed = perf_counter() - start
        assert patch_response.status_code == 200
        single_entity_samples.append(elapsed)

        start = perf_counter()
        confirm_response = await client.post(f"/api/v1/devices/{first_device_id}/confirm")
        elapsed = perf_counter() - start
        assert confirm_response.status_code == 200
        single_entity_samples.append(elapsed)

    list_samples: list[float] = []
    for _ in range(30):
        start = perf_counter()
        list_response = await client.get("/api/v1/devices?sort=name")
        elapsed = perf_counter() - start
        assert list_response.status_code == 200
        list_samples.append(elapsed)

        start = perf_counter()
        filtered_response = await client.get(
            f"/api/v1/devices?device_type_id={device_type_id}&sort=-last_checked_at"
        )
        elapsed = perf_counter() - start
        assert filtered_response.status_code == 200
        list_samples.append(elapsed)

    assert _p95(single_entity_samples) < 0.100
    assert _p95(list_samples) < 0.200
