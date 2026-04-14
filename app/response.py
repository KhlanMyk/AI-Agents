"""Standardized API response wrapper and utilities."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard wrapper for all API responses."""

    success: bool
    """Whether the operation succeeded."""

    data: T | None = None
    """Response payload (None if error)."""

    error: str | None = None
    """Error message if operation failed."""

    timestamp: str
    """ISO 8601 timestamp of response generation."""

    request_id: str | None = None
    """Optional request tracking ID."""

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"status": "ok"},
                "error": None,
                "timestamp": "2026-04-14T12:34:56+00:00",
                "request_id": None,
            }
        }

    @classmethod
    def success_response(
        cls, data: T, request_id: str | None = None
    ) -> "ApiResponse[T]":
        """Create a successful API response."""
        return cls(
            success=True,
            data=data,
            error=None,
            timestamp=datetime.now(UTC).isoformat(),
            request_id=request_id,
        )

    @classmethod
    def error_response(
        cls, error: str, request_id: str | None = None
    ) -> "ApiResponse[T]":
        """Create an error API response."""
        return cls(
            success=False,
            data=None,
            error=error,
            timestamp=datetime.now(UTC).isoformat(),
            request_id=request_id,
        )
