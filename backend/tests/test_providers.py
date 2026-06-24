"""Parser tests against recorded, real-shaped provider responses."""

import json
from pathlib import Path

from app.ingestion.providers import (
    parse_airnow_observations,
    parse_open_meteo,
    parse_openaq_measurements,
)
from app.schemas import AQICategory, Pollutant

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_openaq_parses_pm25_and_skips_unsupported() -> None:
    result = parse_openaq_measurements(load("openaq_measurements.json"), "us-nyc-cp")
    assert result.skipped == 1  # CO is not a tracked pollutant
    assert len(result.measurements) == 2
    first = result.measurements[0]
    assert first.pollutant is Pollutant.pm25
    assert first.value == 12.3
    assert first.unit == "µg/m³"
    assert first.source == "openaq"
    assert first.ts.tzinfo is not None
    assert first.ts.minute == 0  # hour-aligned


def test_openaq_handles_garbage_gracefully() -> None:
    assert parse_openaq_measurements({"results": "not-a-list"}, "x").measurements == []
    assert parse_openaq_measurements({}, "x").measurements == []
    assert parse_openaq_measurements([], "x").measurements == []


def test_airnow_parses_aqi_and_category() -> None:
    observations, skipped = parse_airnow_observations(load("airnow_observations.json"), "us-nyc-cp")
    assert skipped == 0
    assert len(observations) == 2
    pm = observations[0]
    assert pm.parameter == "PM2.5"
    assert pm.aqi == 42
    assert pm.category is AQICategory.good
    assert observations[1].category is AQICategory.moderate


def test_open_meteo_parses_aligned_series() -> None:
    weather = parse_open_meteo(load("open_meteo_forecast.json"), "us-nyc-cp")
    assert len(weather) == 3
    assert weather[0].temperature_c == 18.2
    assert weather[0].humidity_pct == 64
    assert weather[0].wind_speed_ms == 3.2
    assert weather[0].pressure_hpa == 1014.1
    assert weather[0].ts.tzinfo is not None
