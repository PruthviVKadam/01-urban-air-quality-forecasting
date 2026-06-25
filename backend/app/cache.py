"""In-memory TTL caching and Rate Limiting utilities."""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}


def ttl_cache(ttl_seconds: int = 300) -> Callable[..., Any]:
    """A simple in-memory TTL cache decorator for synchronous or async functions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a cache key from func name and arguments.
            # Only use kwargs that are primitive/stringifiable to avoid hashing issues.
            # For FastAPI endpoints, kwargs often contain Depends() objects like `settings` which cannot be hashed.
            # We will build a key using specific keys if needed, or just repr the basic kwargs.
            safe_kwargs = {
                k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))
            }

            key = f"{func.__name__}:{args}:{sorted(safe_kwargs.items())}"

            now = time.monotonic()
            if key in _cache:
                expiry, value = _cache[key]
                if now < expiry:
                    return value

            # Compute
            result = func(*args, **kwargs)
            _cache[key] = (now + ttl_seconds, result)
            return result

        return wrapper

    return decorator


# Rate Limiter
# A simple token bucket or sliding window per IP.
# We'll use a simple dictionary tracking timestamps of requests.
_rate_limits: dict[str, list[float]] = {}


def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """Returns True if the key has exceeded max_requests in the past window_seconds."""
    now = time.monotonic()

    if key not in _rate_limits:
        _rate_limits[key] = [now]
        return False

    # Filter out old requests
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window_seconds]

    if len(_rate_limits[key]) >= max_requests:
        return True

    _rate_limits[key].append(now)
    return False
