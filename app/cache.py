"""Caching utilities for optimized query performance."""

import time
from functools import wraps
from typing import Any, Callable, TypeVar


T = TypeVar("T")

_CACHE_REGISTRY: dict[str, dict[tuple[Any, ...], tuple[Any, float]]] = {}


def cache_with_ttl(ttl_seconds: int = 60, namespace: str | None = None) -> Callable:
    """
    Decorator for function-level caching with time-to-live support.

    Args:
        ttl_seconds: Cache validity duration in seconds.
        namespace: Shared cache namespace for related functions.

    Returns:
        Decorated function that caches results.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_name = namespace or func.__name__
        cache = _CACHE_REGISTRY.setdefault(cache_name, {})

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = (args, tuple(sorted(kwargs.items())))

            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    return result

            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result

        return wrapper

    return decorator


def invalidate_cache(namespace: str) -> None:
    """Clear all cached values for a namespace."""
    if namespace in _CACHE_REGISTRY:
        _CACHE_REGISTRY[namespace].clear()
