"""API contract — these Pydantic models ARE the OpenAPI schema.

Frontend TypeScript types are generated from this contract (`scripts/export_openapi.py`
-> `openapi.json` -> `openapi-typescript`). Never hand-sync request/response shapes.

The hard limits in `rules.md` are encoded structurally here so the contract itself
enforces them:

* HL1 (freshness)      -> ``data_as_of`` + ``stale`` on every data-bearing payload.
* HL2 (baseline shadow)-> ``baseline`` per point + ``beats_baseline`` per forecast.
* HL3 (no silent fill) -> ``interpolated`` flag on every reading / forecast point.
* HL4 (not medical)    -> ``disclaimer`` string carried on every forecast.
"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Pollutant(StrEnum):
    """Pollutants this app forecasts."""

    pm25 = "pm25"
    o3 = "o3"
    no2 = "no2"


class AQICategory(StrEnum):
    """US EPA AQI categories (display + color encoding only — see HL4)."""

    good = "good"
    moderate = "moderate"
    unhealthy_sensitive = "unhealthy_sensitive"
    unhealthy = "unhealthy"
    very_unhealthy = "very_unhealthy"
    hazardous = "hazardous"


class DataSource(StrEnum):
    """Provenance of a payload so the UI can be honest about what it shows."""

    live = "live"  # fresh from upstream + validated model
    seed = "seed"  # Phase 0 placeholder, clearly labeled in the UI
    cache = "cache"  # last-known-good served during an upstream outage (HL5)


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class LatestReading(BaseModel):
    """Most recent observed value for one pollutant at a station."""

    pollutant: Pollutant
    value: float = Field(..., ge=0, description="Concentration; never negative.")
    unit: str
    aqi: int = Field(..., ge=0)
    category: AQICategory
    interpolated: bool = Field(..., description="HL3 — true if imputed, not measured.")
    observed_at: datetime


class Station(BaseModel):
    id: str
    name: str
    city: str
    country: str
    coordinates: Coordinates
    pollutants: list[Pollutant]
    latest: list[LatestReading]
    data_as_of: datetime = Field(..., description="HL1 — freshness of this station's data.")
    stale: bool = Field(..., description="HL1 — true when data_as_of is older than the threshold.")
    data_source: DataSource


class ForecastPoint(BaseModel):
    ts: datetime
    value: float = Field(..., ge=0, description="Predicted concentration; never negative.")
    lower: float = Field(..., ge=0, description="Confidence-interval lower bound.")
    upper: float = Field(..., ge=0, description="Confidence-interval upper bound.")
    baseline: float = Field(..., ge=0, description="HL2 — persistence-baseline value at this ts.")
    aqi: int = Field(..., ge=0)
    category: AQICategory
    interpolated: bool = Field(..., description="HL3 — true if derived from imputed inputs.")


class ForecastResponse(BaseModel):
    station_id: str
    station_name: str
    pollutant: Pollutant
    unit: str
    horizon_hours: int = Field(..., ge=1, le=24)
    generated_at: datetime
    data_as_of: datetime = Field(..., description="HL1 — freshness of the inputs.")
    stale: bool = Field(..., description="HL1.")
    data_source: DataSource
    model_version: str = Field(..., description="HL2 — identifies the serving model.")
    baseline_label: str = Field(..., description="HL2 — name of the baseline (e.g. 'persistence').")
    beats_baseline: bool = Field(
        ..., description="HL2 — whether the model beats the baseline on the validation window."
    )
    disclaimer: str = Field(..., description="HL4 — not-medical-guidance notice.")
    points: list[ForecastPoint]


class UpstreamStatus(StrEnum):
    ok = "ok"
    degraded = "degraded"
    down = "down"
    unknown = "unknown"


class ProviderHealth(BaseModel):
    name: str
    status: UpstreamStatus
    last_success: datetime | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    time: datetime
    uptime_seconds: float
    last_refresh: datetime | None = Field(
        None, description="When forecasts were last refreshed; null before Phase 1."
    )
    data_as_of: datetime | None = None
    upstreams: list[ProviderHealth]
    cache_hit_rate: float | None = Field(None, ge=0, le=1)


class ErrorResponse(BaseModel):
    """Uniform error envelope; never leaks internals to the client (HL5)."""

    error: str
    code: str
    detail: str | None = None
    request_id: str | None = None
