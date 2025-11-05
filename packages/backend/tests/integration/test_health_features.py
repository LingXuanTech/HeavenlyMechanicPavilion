"""Integration tests for the feature completeness health endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_features_endpoint(async_client: AsyncClient) -> None:
    """GET /health/features should report all registered features as complete."""

    response = await async_client.get("/health/features")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == len(payload["checks"])
    assert payload["passed"] + payload["failed"] == payload["total"]

    # With the current implementation all feature checks should pass.
    assert payload["status"] == "complete"
    assert payload["failed"] == 0
    assert all(check["passed"] for check in payload["checks"])
