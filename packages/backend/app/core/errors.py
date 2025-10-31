"""Custom exception hierarchy for the TradingAgents backend."""

from __future__ import annotations

from typing import Any, Dict, Optional, TypeVar

from fastapi import status


class TradingAgentsError(Exception):
    """Base class for application-specific exceptions."""

    default_message = "An unexpected error occurred."
    code = "tradingagents_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.code = (code or self.code).lower().replace(" ", "_")
        self.status_code = status_code or self.status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the exception to a JSON-ready dictionary."""
        payload: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload


class ValidationError(TradingAgentsError):
    """Raised when user input fails validation rules."""

    default_message = "Request validation failed."
    code = "validation_error"
    status_code = status.HTTP_400_BAD_REQUEST


class ResourceNotFoundError(TradingAgentsError):
    """Raised when a requested resource cannot be found."""

    default_message = "Requested resource was not found."
    code = "resource_not_found"
    status_code = status.HTTP_404_NOT_FOUND


class ExternalServiceError(TradingAgentsError):
    """Raised when an upstream service fails."""

    default_message = "Upstream service is unavailable."
    code = "external_service_error"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class VendorAPIError(ExternalServiceError):
    """Raised when a vendor or data provider request fails."""

    default_message = "Vendor API call failed."
    code = "vendor_api_error"
    status_code = status.HTTP_502_BAD_GATEWAY


class RiskConstraintViolation(TradingAgentsError):
    """Raised when risk controls reject an operation."""

    default_message = "Risk constraints were violated."
    code = "risk_constraint_violation"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class InsufficientFundsError(TradingAgentsError):
    """Raised when an operation cannot proceed because of capital constraints."""

    default_message = "Insufficient funds to complete the operation."
    code = "insufficient_funds"
    status_code = status.HTTP_409_CONFLICT


class CircuitBreakerOpenError(ExternalServiceError):
    """Raised when a circuit breaker prevents an external call."""

    default_message = "Circuit breaker is open for this dependency."
    code = "circuit_breaker_open"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


TAE = TypeVar("TAE", bound=TradingAgentsError)


__all__ = [
    "CircuitBreakerOpenError",
    "ExternalServiceError",
    "InsufficientFundsError",
    "ResourceNotFoundError",
    "RiskConstraintViolation",
    "TradingAgentsError",
    "ValidationError",
    "VendorAPIError",
    "TAE",
]
