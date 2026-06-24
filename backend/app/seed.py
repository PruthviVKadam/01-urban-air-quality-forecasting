"""Deterministic SEED provider for Phase 0.

This exists so the full contract is exercisable (and the frontend's loading/empty/
error/stale states + type generation can be built) before the real ETL (Phase 1) and
model (Phase 3) land. Everything it returns is labeled ``data_source="seed"`` and
``model_version="seed-*"`` with ``beats_baseline=False`` — it never claims to be a
validated measurement or to beat the baseline (HL2). Output is deterministic per
clock-hour so responses are reproducible within a session.
"""

import math
from datetime import UTC, datetime, timedelta
from random import Random

from app.aqi import aqi_for, category_from_aqi
from app.config import get_settings
from app.constants import DISCLAIMER, SEED_MODEL_VERSION, UNITS
from app.schemas import (
    Coordinates,
    DataSource,
    ForecastPoint,
    ForecastResponse,
    LatestReading,
    Pollutant,
    Station,
)

# (id, name, city, country, lat, lon, base_pm25) — real cities, plausible coordinates.
_STATION_META: list[tuple[str, str, str, str, float, float, float]] = [
    ("us-nyc-cp", "Central Park", "New York", "US", 40.7829, -73.9654, 11.0),
    ("us-la-dt", "Downtown LA", "Los Angeles", "US", 34.0407, -118.2468, 18.0),
    ("in-del-anand", "Anand Vihar", "Delhi", "IN", 28.6469, 77.3162, 92.0),
    ("gb-lon-marylebone", "Marylebone Road", "London", "GB", 51.5225, -0.1547, 14.0),
    ("jp-tok-shinjuku", "Shinjuku", "Tokyo", "JP", 35.6896, 139.6917, 13.0),
]

# Relative pollutant levels vs the station's base PM2.5 anchor.
_POLLUTANT_FACTOR: dict[Pollutant, float] = {
    Pollutant.pm25: 1.0,
    Pollutant.o3: 2.4,
    Pollutant.no2: 1.8,
}


def _now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _diurnal(hour: int) -> float:
    """Daily pollution cycle ~ peaks at rush hours; bounded ~[0.7, 1.3]."""
    return 1.0 + 0.3 * math.sin((hour - 8) / 24 * 2 * math.pi)


def _hour_seed(station_id: str, now: datetime) -> int:
    return abs(hash((station_id, now.strftime("%Y-%m-%dT%H")))) % (2**32)


def _base_value(base_pm25: float, pollutant: Pollutant, hour: int, rng: Random) -> float:
    raw = base_pm25 * _POLLUTANT_FACTOR[pollutant] * _diurnal(hour) * (0.9 + 0.2 * rng.random())
    return round(max(raw, 0.0), 1)


def get_seed_stations() -> list[Station]:
    now = _now()
    stations: list[Station] = []
    for sid, name, city, country, lat, lon, base in _STATION_META:
        rng = Random(_hour_seed(sid, now))
        readings: list[LatestReading] = []
        for pollutant in Pollutant:
            value = _base_value(base, pollutant, now.hour, rng)
            aqi = aqi_for(pollutant, value)
            readings.append(
                LatestReading(
                    pollutant=pollutant,
                    value=value,
                    unit=UNITS[pollutant],
                    aqi=aqi,
                    category=category_from_aqi(aqi),
                    interpolated=False,
                    observed_at=now,
                )
            )
        stations.append(
            Station(
                id=sid,
                name=name,
                city=city,
                country=country,
                coordinates=Coordinates(lat=lat, lon=lon),
                pollutants=list(Pollutant),
                latest=readings,
                data_as_of=now,
                stale=False,
                data_source=DataSource.seed,
            )
        )
    return stations


def get_seed_station(station_id: str) -> Station | None:
    return next((s for s in get_seed_stations() if s.id == station_id), None)


def build_seed_forecast(
    station: Station, pollutant: Pollutant, horizon_hours: int
) -> ForecastResponse:
    now = _now()
    last = next(r.value for r in station.latest if r.pollutant == pollutant)
    rng = Random(_hour_seed(f"{station.id}:{pollutant.value}", now))

    points: list[ForecastPoint] = []
    for h in range(1, horizon_hours + 1):
        ts = now + timedelta(hours=h)
        trend = _diurnal(ts.hour) / _diurnal(now.hour)
        value = max(last * trend * (1 + rng.uniform(-0.05, 0.05)), 0.0)
        spread = value * (0.08 + 0.012 * h)  # CI widens with horizon
        aqi = aqi_for(pollutant, value)
        points.append(
            ForecastPoint(
                ts=ts,
                value=round(value, 1),
                lower=round(max(value - spread, 0.0), 1),
                upper=round(value + spread, 1),
                baseline=round(last, 1),  # HL2 — persistence
                aqi=aqi,
                category=category_from_aqi(aqi),
                interpolated=False,
            )
        )

    return ForecastResponse(
        station_id=station.id,
        station_name=station.name,
        pollutant=pollutant,
        unit=UNITS[pollutant],
        horizon_hours=horizon_hours,
        generated_at=now,
        data_as_of=now,
        stale=False,
        data_source=DataSource.seed,
        model_version=SEED_MODEL_VERSION,
        baseline_label="persistence",
        beats_baseline=False,  # honest: no validated model exists yet (HL2)
        disclaimer=DISCLAIMER,
        points=points,
    )


def max_horizon_hours() -> int:
    return get_settings().max_horizon_hours
