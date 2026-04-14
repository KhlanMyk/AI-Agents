"""Caching utilities for optimized query performance."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar


T = TypeVar("T")


def cache_with_ttl(ttl_seconds: int = 60) -> Callable:
    """
    Decorator for function-level caching with time-to-live support.

    Args:
        ttl_seconds: Cache validity duration in seconds.

    Returns:
        Decorated function that caches results.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache: dict[tuple[Any, ...], tuple[T, float]] = {}

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Build cache key from function args/kwargs
            key = (args, tuple(sorted(kwargs.items())))

            # Check if cached and not expired
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result

            # Compute result and cache it
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result

        return wrapper

    return decorator
