"""Provider clients and parsers for OpenAQ, AirNow, and Open-Meteo."""

from app.ingestion.providers.airnow import AirNowClient, parse_airnow_observations
from app.ingestion.providers.base import (
    AqiObservation,
    ParseResult,
    WeatherObservation,
    build_client,
    resolve_api_key,
)
from app.ingestion.providers.open_meteo import OpenMeteoClient, parse_open_meteo
from app.ingestion.providers.openaq import OpenAQClient, parse_openaq_measurements

__all__ = [
    "AirNowClient",
    "AqiObservation",
    "OpenAQClient",
    "OpenMeteoClient",
    "ParseResult",
    "WeatherObservation",
    "build_client",
    "parse_airnow_observations",
    "parse_open_meteo",
    "parse_openaq_measurements",
    "resolve_api_key",
]
