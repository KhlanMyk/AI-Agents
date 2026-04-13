"""Time utilities for consistent UTC handling across the app."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a timezone-aware current UTC datetime."""
    return datetime.now(UTC)
