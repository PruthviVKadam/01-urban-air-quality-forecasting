"""OpenAQ v3 — primary pollutant feed (concentrations).

Parses the v3 measurements result shape (parameter name/units + period.datetimeFrom.utc),
tolerating the older `date.utc` form. Structurally-broken results are skipped and counted.
"""

from datetime import datetime
from typing import Any

from app.constants import UNITS
from app.ingestion.models import Measurement
from app.ingestion.providers.base import ParseResult
from app.ingestion.resilient_client import FetchResult, ResilientHttpClient
from app.ingestion.timeutil import floor_to_hour, parse_iso_utc
from app.schemas import Pollutant

OPENAQ_PARAM_MAP: dict[str, Pollutant] = {
    "pm25": Pollutant.pm25,
    "pm2.5": Pollutant.pm25,
    "o3": Pollutant.o3,
    "ozone": Pollutant.o3,
    "no2": Pollutant.no2,
}


def _extract_ts(result: dict[str, Any]) -> datetime:
    period = result.get("period")
    if isinstance(period, dict):
        start = period.get("datetimeFrom")
        if isinstance(start, dict) and start.get("utc"):
            return parse_iso_utc(start["utc"])
    date = result.get("date")
    if isinstance(date, dict) and date.get("utc"):
        return parse_iso_utc(date["utc"])
    if isinstance(result.get("datetime"), str):
        return parse_iso_utc(result["datetime"])
    raise KeyError("no timestamp in result")


def parse_openaq_measurements(payload: Any, station_id: str) -> ParseResult:
    out = ParseResult()
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return out
    for result in results:
        try:
            param = result["parameter"]
            name = (param["name"] if isinstance(param, dict) else str(param)).lower()
            pollutant = OPENAQ_PARAM_MAP.get(name)
            if pollutant is None:
                out.skipped += 1
                continue
            units = (
                (param.get("units") if isinstance(param, dict) else None)
                or result.get("unit")
                or UNITS[pollutant]
            )
            ts = floor_to_hour(_extract_ts(result))
            value = float(result["value"])
            out.measurements.append(
                Measurement(station_id, pollutant, ts, value, units, "openaq")
            )
        except (KeyError, TypeError, ValueError):
            out.skipped += 1
    return out


class OpenAQClient:
    def __init__(self, client: ResilientHttpClient, api_key: str | None) -> None:
        self._client = client
        self._api_key = api_key

    def fetch_measurements(
        self,
        sensor_id: int | str,
        station_id: str,
        *,
        date_from: datetime,
        date_to: datetime,
        limit: int = 1000,
    ) -> tuple[FetchResult, ParseResult]:
        headers = {"X-API-Key": self._api_key} if self._api_key else None
        result = self._client.get_json(
            f"/sensors/{sensor_id}/measurements",
            params={
                "datetime_from": date_from.isoformat(),
                "datetime_to": date_to.isoformat(),
                "limit": limit,
            },
            headers=headers,
            cache_key=f"openaq:meas:{sensor_id}:{date_from.isoformat()}:{date_to.isoformat()}",
        )
        return result, parse_openaq_measurements(result.data, station_id)
