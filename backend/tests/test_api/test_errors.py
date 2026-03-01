"""Integration tests for health endpoint and standardized error responses."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_endpoint_returns_ok_status(client: AsyncClient) -> None:
    """Health endpoint should return service status and correlation header."""

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("X-Correlation-ID")


async def test_invalid_correlation_id_returns_validation_error(client: AsyncClient) -> None:
    """Middleware should reject invalid correlation IDs with VALIDATION_ERROR envelope."""

    response = await client.get("/api/v1/health", headers={"X-Correlation-ID": "a" * 129})

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Header X-Correlation-ID must be 1-128 printable ASCII characters.",
        "error_code": "VALIDATION_ERROR",
        "field": "X-Correlation-ID",
    }
    assert response.headers.get("X-Correlation-ID")
