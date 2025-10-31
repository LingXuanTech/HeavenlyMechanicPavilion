"""Tests for the global error handling middleware."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.errors import VendorAPIError
from app.main import app

# Register test-only routes once
_TEST_ROUTER = APIRouter()


@_TEST_ROUTER.get("/__test__/vendor-error")
async def trigger_vendor_error() -> None:
    raise VendorAPIError(
        "Vendor offline",
        details={"vendor": "alpha_vantage"},
    )


@_TEST_ROUTER.get("/__test__/http-error")
async def trigger_http_error() -> None:
    raise HTTPException(status_code=404, detail="not found")


@_TEST_ROUTER.get("/__test__/requires-param")
async def requires_param(limit: int) -> dict[str, int]:
    return {"limit": limit}


if not any(route.path == "/__test__/vendor-error" for route in app.router.routes):
    app.include_router(_TEST_ROUTER)


def test_vendor_error_response(sync_client) -> None:
    response = sync_client.get("/__test__/vendor-error")

    assert response.status_code == 502
    payload = response.json()

    assert payload["error"]["code"] == "vendor_api_error"
    assert "correlation_id" in payload
    assert response.headers["X-Correlation-ID"] == payload["correlation_id"]


def test_correlation_id_passthrough(sync_client) -> None:
    correlation_id = "test-correlation-id"
    response = sync_client.get(
        "/__test__/vendor-error",
        headers={"X-Correlation-ID": correlation_id},
    )

    assert response.status_code == 502
    assert response.headers["X-Correlation-ID"] == correlation_id
    assert response.json()["correlation_id"] == correlation_id


def test_http_exception_shape(sync_client) -> None:
    response = sync_client.get("/__test__/http-error")

    assert response.status_code == 404
    payload = response.json()

    assert payload["error"]["code"] == "http_error"
    assert payload["error"]["message"] == "not found"


def test_request_validation_error(sync_client) -> None:
    response = sync_client.get("/__test__/requires-param")

    assert response.status_code == 422
    payload = response.json()

    assert payload["error"]["code"] == "validation_error"
    assert "errors" in payload["error"]["details"]
