"""AirNow — official US AQI + EPA category enrichment (display text only, HL4).

AirNow reports AQI (not raw concentration), so it enriches the EPA category text rather
than feeding the concentration pipeline. Treated as optional: the app still forecasts if
AirNow is down.
"""

from datetime import datetime
from typing import Any

from app.ingestion.providers.base import AqiObservation
from app.ingestion.resilient_client import FetchResult, ResilientHttpClient
from app.ingestion.timeutil import floor_to_hour, parse_iso_utc
from app.schemas import AQICategory

AIRNOW_CATEGORY_MAP: dict[str, AQICategory] = {
    "good": AQICategory.good,
    "moderate": AQICategory.moderate,
    "unhealthy for sensitive groups": AQICategory.unhealthy_sensitive,
    "unhealthy": AQICategory.unhealthy,
    "very unhealthy": AQICategory.very_unhealthy,
    "hazardous": AQICategory.hazardous,
}


def parse_airnow_observations(payload: Any, station_id: str) -> tuple[list[AqiObservation], int]:
    if not isinstance(payload, list):
        return [], 0
    observations: list[AqiObservation] = []
    skipped = 0
    for item in payload:
        try:
            category = AIRNOW_CATEGORY_MAP.get(str(item["Category"]["Name"]).strip().lower())
            if category is None:
                skipped += 1
                continue
            date = str(item["DateObserved"]).strip()
            hour = int(item["HourObserved"])
            # AirNow reports local time; we align to the reported wall-clock hour. A future
            # refinement maps LocalTimeZone -> UTC offset precisely.
            ts = floor_to_hour(parse_iso_utc(f"{date}T{hour:02d}:00:00"))
            observations.append(
                AqiObservation(
                    station_id=station_id,
                    ts=ts,
                    parameter=str(item["ParameterName"]).strip(),
                    aqi=int(item["AQI"]),
                    category=category,
                )
            )
        except (KeyError, TypeError, ValueError):
            skipped += 1
    return observations, skipped


class AirNowClient:
    def __init__(self, client: ResilientHttpClient, api_key: str | None) -> None:
        self._client = client
        self._api_key = api_key

    def fetch_current(
        self, latitude: float, longitude: float, station_id: str
    ) -> tuple[FetchResult, list[AqiObservation]]:
        result = self._client.get_json(
            "/aq/observation/latLong/current/",
            params={
                "format": "application/json",
                "latitude": latitude,
                "longitude": longitude,
                "API_KEY": self._api_key or "",
            },
            cache_key=f"airnow:current:{latitude}:{longitude}",
        )
        observations, _ = parse_airnow_observations(result.data, station_id)
        return result, observations
