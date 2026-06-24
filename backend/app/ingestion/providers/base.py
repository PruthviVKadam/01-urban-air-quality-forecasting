"""Shared provider types and a factory for building resilient clients."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.config import PROVIDERS, Settings
from app.ingestion.cache import LastKnownGoodCache
from app.ingestion.models import Measurement
from app.ingestion.resilient_client import ResilientHttpClient
from app.schemas import AQICategory


@dataclass
class ParseResult:
    """Parsed measurements plus a count of structurally-broken entries skipped.

    Skips are surfaced (not hidden) so corrupt upstream rows are observable; value-level
    quality (range/gap/dup) is handled later by validation, never at parse time.
    """

    measurements: list[Measurement] = field(default_factory=list)
    skipped: int = 0


@dataclass(frozen=True, slots=True)
class WeatherObservation:
    """Exogenous weather features (Open-Meteo), used by Phase 2 feature engineering."""

    station_id: str
    ts: datetime
    temperature_c: float | None
    humidity_pct: float | None
    wind_speed_ms: float | None
    pressure_hpa: float | None


@dataclass(frozen=True, slots=True)
class AqiObservation:
    """AirNow enrichment — official AQI + EPA category (display text only, HL4)."""

    station_id: str
    ts: datetime
    parameter: str
    aqi: int
    category: AQICategory


def build_client(
    provider_key: str,
    cache_root: Path,
    settings: Settings,
    *,
    transport: object | None = None,
) -> ResilientHttpClient:
    """Construct a resilient client for a provider, wiring its cache directory."""
    config = PROVIDERS[provider_key]
    cache = LastKnownGoodCache(Path(cache_root) / provider_key)
    return ResilientHttpClient(config, cache, transport=transport)  # type: ignore[arg-type]


def resolve_api_key(provider_key: str, settings: Settings) -> str | None:
    config = PROVIDERS[provider_key]
    if config.api_key_env is None:
        return None
    return getattr(settings, config.api_key_env.lower(), None)
