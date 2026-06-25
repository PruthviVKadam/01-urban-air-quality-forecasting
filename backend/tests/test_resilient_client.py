from collections.abc import Iterable
from pathlib import Path
from random import Random

import httpx
import pytest
from app.config import ProviderConfig
from app.ingestion.cache import LastKnownGoodCache
from app.ingestion.circuit_breaker import BreakerState, CircuitBreaker
from app.ingestion.errors import CircuitOpenError, UpstreamError
from app.ingestion.resilient_client import ResilientHttpClient

ScriptItem = tuple[int, dict[str, str | int]] | Exception


def make_transport(script: Iterable[ScriptItem]) -> tuple[httpx.MockTransport, list[int]]:
    it = iter(script)
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        item = next(it)
        if isinstance(item, Exception):
            raise item
        status, body = item
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler), calls


class RecordingSleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, secs: float) -> None:
        self.calls.append(secs)


def make_client(
    tmp: Path,
    script: Iterable[ScriptItem],
    *,
    retry_max: int = 3,
    breaker: CircuitBreaker | None = None,
) -> tuple[ResilientHttpClient, list[int], RecordingSleep]:
    cfg = ProviderConfig(
        name="Test",
        base_url="https://test.local",
        timeout_s=1.0,
        retry_max=retry_max,
        backoff_base_s=0.01,
        failure_threshold=2,
    )
    transport, calls = make_transport(script)
    sleep = RecordingSleep()
    client = ResilientHttpClient(
        cfg,
        LastKnownGoodCache(tmp / "cache"),
        breaker=breaker,
        transport=transport,
        sleep=sleep,
        rng=Random(0),
    )
    return client, calls, sleep


def test_success_first_try(tmp_path: Path) -> None:
    client, calls, sleep = make_client(tmp_path, [(200, {"ok": 1})])
    result = client.get_json("/x", cache_key="k")
    assert result.data == {"ok": 1}
    assert result.stale is False
    assert len(calls) == 1
    assert sleep.calls == []


def test_retries_then_succeeds(tmp_path: Path) -> None:
    client, calls, sleep = make_client(tmp_path, [(503, {}), (500, {}), (200, {"ok": 2})])
    result = client.get_json("/x", cache_key="k")
    assert result.data == {"ok": 2}
    assert len(calls) == 3
    assert len(sleep.calls) == 2  # backoff between the 3 attempts


def test_timeout_is_retried(tmp_path: Path) -> None:
    err = httpx.ConnectTimeout("timed out")
    client, calls, _ = make_client(tmp_path, [err, (200, {"ok": 3})])
    result = client.get_json("/x", cache_key="k")
    assert result.data == {"ok": 3}
    assert len(calls) == 2


def test_exhausted_serves_last_known_good(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path, [(500, {})] * 4)
    client._cache.set("k", {"cached": True})  # pre-seed last-known-good
    result = client.get_json("/x", cache_key="k")
    assert result.stale is True
    assert result.from_cache is True
    assert result.data == {"cached": True}


def test_exhausted_without_cache_raises(tmp_path: Path) -> None:
    client, _, _ = make_client(tmp_path, [(500, {})] * 4)
    with pytest.raises(UpstreamError):
        client.get_json("/x", cache_key="k")


def test_non_retryable_4xx_raises_immediately(tmp_path: Path) -> None:
    client, calls, sleep = make_client(tmp_path, [(404, {"detail": "nope"})])
    with pytest.raises(UpstreamError) as exc:
        client.get_json("/x", cache_key="k")
    assert exc.value.status == 404
    assert len(calls) == 1  # no retries
    assert sleep.calls == []


def test_open_circuit_short_circuits_to_cache(tmp_path: Path) -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout_s=100)
    client, calls, _ = make_client(tmp_path, [(500, {})] * 8, retry_max=0, breaker=breaker)
    client._cache.set("k", {"cached": True})

    first = client.get_json("/x", cache_key="k")  # fails once, opens, falls back
    assert first.stale is True
    assert breaker.state is BreakerState.open

    calls_before = len(calls)
    second = client.get_json("/x", cache_key="k")  # short-circuits, no network call
    assert second.stale is True
    assert len(calls) == calls_before


def test_open_circuit_without_cache_raises(tmp_path: Path) -> None:
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout_s=100)
    client, _, _ = make_client(tmp_path, [(500, {})] * 4, retry_max=0, breaker=breaker)
    with pytest.raises(UpstreamError):
        client.get_json("/x", cache_key="k")  # opens breaker
    with pytest.raises(CircuitOpenError):
        client.get_json("/x", cache_key="k")  # now short-circuits with no cache
