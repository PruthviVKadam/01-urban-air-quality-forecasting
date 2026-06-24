"""A minimal circuit breaker (closed → open → half-open).

After ``failure_threshold`` consecutive failures the breaker opens and short-circuits
calls for ``recovery_timeout_s``; it then allows a single probe (half-open). A success
closes it; a failure re-opens it. The clock is injectable for deterministic tests.
"""

from collections.abc import Callable
from enum import StrEnum
from time import monotonic


class BreakerState(StrEnum):
    closed = "closed"
    open = "open"
    half_open = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 30.0,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout_s = recovery_timeout_s
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> BreakerState:
        if self._opened_at is None:
            return BreakerState.closed
        if self._clock() - self._opened_at >= self._recovery_timeout_s:
            return BreakerState.half_open
        return BreakerState.open

    def allow(self) -> bool:
        """Whether a request may proceed right now."""
        return self.state is not BreakerState.open

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        # A failed half-open probe re-opens immediately.
        if self.state is BreakerState.half_open:
            self._opened_at = self._clock()
            return
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._opened_at = self._clock()
