"""HTTP client that assumes every upstream is unreliable (HL5).

Layers, in order: a per-request timeout, retry with exponential backoff + jitter on
transient failures (timeouts, transport errors, 429, 5xx), a circuit breaker that
short-circuits a flapping upstream, and a last-known-good cache so a hard failure
degrades to stale data instead of an error. Non-retryable 4xx errors surface
immediately (fail loud — likely our bug, not the upstream's).
"""

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import ProviderConfig
from app.ingestion.cache import LastKnownGoodCache
from app.ingestion.circuit_breaker import CircuitBreaker
from app.ingestion.errors import CircuitOpenError, UpstreamError

logger = logging.getLogger("uaqf.ingestion")

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class FetchResult:
    data: Any
    stale: bool  # served from last-known-good fallback (HL1/HL5)
    from_cache: bool


class ResilientHttpClient:
    def __init__(
        self,
        config: ProviderConfig,
        cache: LastKnownGoodCache,
        *,
        breaker: CircuitBreaker | None = None,
        transport: httpx.BaseTransport | None = None,
        default_headers: dict[str, str] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._config = config
        self._cache = cache
        self._breaker = breaker or CircuitBreaker(
            failure_threshold=config.failure_threshold,
            recovery_timeout_s=config.recovery_timeout_s,
        )
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout_s,
            transport=transport,
            headers=default_headers or {},
        )

    @property
    def breaker(self) -> CircuitBreaker:
        return self._breaker

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ResilientHttpClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _backoff(self, attempt: int) -> float:
        # Exponential base with full jitter: base * 2**attempt * U(0.5, 1.5).
        return float(self._config.backoff_base_s * (2**attempt) * (0.5 + self._rng.random()))

    def _serve_stale(self, cache_key: str) -> FetchResult | None:
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        return FetchResult(data=entry.value, stale=True, from_cache=True)

    def get_json(
        self,
        path: str,
        *,
        cache_key: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FetchResult:
        provider = self._config.name

        if not self._breaker.allow():
            stale = self._serve_stale(cache_key)
            if stale is not None:
                logger.warning("circuit_open_serving_cache", extra={"provider": provider})
                return stale
            raise CircuitOpenError(provider, "circuit open and no cached data available")

        last_status: int | None = None
        for attempt in range(self._config.retry_max + 1):
            try:
                resp = self._client.get(path, params=params, headers=headers)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_status = None
                self._breaker.record_failure()
                logger.warning(
                    "upstream_transport_error",
                    extra={"provider": provider, "attempt": attempt, "error": str(exc)},
                )
            else:
                if resp.is_success:
                    data = resp.json()
                    self._cache.set(cache_key, data)
                    self._breaker.record_success()
                    return FetchResult(data=data, stale=False, from_cache=False)
                last_status = resp.status_code
                if resp.status_code not in _RETRYABLE_STATUS:
                    # Non-retryable client error — surface immediately.
                    raise UpstreamError(provider, "non-retryable response", status=resp.status_code)
                self._breaker.record_failure()
                logger.warning(
                    "upstream_retryable_status",
                    extra={"provider": provider, "attempt": attempt, "status": resp.status_code},
                )

            if attempt < self._config.retry_max:
                self._sleep(self._backoff(attempt))

        # Retries exhausted — degrade to last-known-good if we have it (HL5).
        stale = self._serve_stale(cache_key)
        if stale is not None:
            logger.warning("upstream_exhausted_serving_cache", extra={"provider": provider})
            return stale
        raise UpstreamError(
            provider, f"all {self._config.retry_max + 1} attempts failed", status=last_status
        )
