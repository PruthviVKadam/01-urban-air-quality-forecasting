"""Open-Meteo — weather (exogenous features). No API key required."""

from typing import Any

from app.ingestion.providers.base import WeatherObservation
from app.ingestion.resilient_client import FetchResult, ResilientHttpClient
from app.ingestion.timeutil import floor_to_hour, parse_iso_utc

_HOURLY_VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,surface_pressure"


def _at(values: list[Any], i: int) -> float | None:
    if i < len(values) and values[i] is not None:
        try:
            return float(values[i])
        except (TypeError, ValueError):
            return None
    return None


def parse_open_meteo(payload: Any, station_id: str) -> list[WeatherObservation]:
    hourly = payload.get("hourly") if isinstance(payload, dict) else None
    if not isinstance(hourly, dict):
        return []
    times = hourly.get("time") or []
    temp = hourly.get("temperature_2m") or []
    humidity = hourly.get("relative_humidity_2m") or []
    wind = hourly.get("wind_speed_10m") or []
    pressure = hourly.get("surface_pressure") or []

    observations: list[WeatherObservation] = []
    for i, raw_ts in enumerate(times):
        try:
            ts = floor_to_hour(parse_iso_utc(str(raw_ts)))
        except (TypeError, ValueError):
            continue
        observations.append(
            WeatherObservation(
                station_id=station_id,
                ts=ts,
                temperature_c=_at(temp, i),
                humidity_pct=_at(humidity, i),
                wind_speed_ms=_at(wind, i),
                pressure_hpa=_at(pressure, i),
            )
        )
    return observations


class OpenMeteoClient:
    def __init__(self, client: ResilientHttpClient) -> None:
        self._client = client

    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        station_id: str,
        *,
        past_days: int = 2,
        forecast_days: int = 2,
    ) -> tuple[FetchResult, list[WeatherObservation]]:
        result = self._client.get_json(
            "/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": _HOURLY_VARS,
                "past_days": past_days,
                "forecast_days": forecast_days,
                "timezone": "UTC",
            },
            cache_key=f"openmeteo:{latitude}:{longitude}:{past_days}:{forecast_days}",
        )
        return result, parse_open_meteo(result.data, station_id)
