from app.ingestion.circuit_breaker import BreakerState, CircuitBreaker


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_opens_after_threshold() -> None:
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout_s=10, clock=clock)
    assert cb.allow()
    cb.record_failure()
    cb.record_failure()
    assert cb.allow()  # still closed at 2 < 3
    cb.record_failure()
    assert cb.state is BreakerState.open
    assert not cb.allow()


def test_half_open_after_recovery_then_success_closes() -> None:
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=10, clock=clock)
    cb.record_failure()
    assert cb.state is BreakerState.open
    clock.advance(10)
    assert cb.state is BreakerState.half_open
    assert cb.allow()
    cb.record_success()
    assert cb.state is BreakerState.closed


def test_half_open_failure_reopens() -> None:
    clock = FakeClock()
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=10, clock=clock)
    cb.record_failure()
    clock.advance(10)
    assert cb.state is BreakerState.half_open
    cb.record_failure()  # failed probe
    assert cb.state is BreakerState.open
