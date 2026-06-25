"""Tests for WeatherStore DuckDB operations."""

from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.providers.base import WeatherObservation
from app.ingestion.weather_store import WeatherStore


def test_weather_store_idempotent_upsert(tmp_path: Path) -> None:
    store = WeatherStore(tmp_path / "weather.parquet")

    # 1. Insert initial
    obs1 = [
        WeatherObservation(
            station_id="s1",
            ts=datetime(2025, 1, 1, 12, tzinfo=UTC),
            temperature_c=20.5,
            humidity_pct=45.0,
            wind_speed_ms=3.2,
            pressure_hpa=1013.2,
        )
    ]
    assert store.upsert(obs1) == 1
    assert store.count() == 1

    # 2. Upsert same (idempotent)
    assert store.upsert(obs1) == 1
    assert store.count() == 1

    # 3. Upsert update (different values, same key)
    obs1_updated = [
        WeatherObservation(
            station_id="s1",
            ts=datetime(2025, 1, 1, 12, tzinfo=UTC),
            temperature_c=21.0,
            humidity_pct=40.0,
            wind_speed_ms=4.0,
            pressure_hpa=1012.0,
        )
    ]
    assert store.upsert(obs1_updated) == 1
    assert store.count() == 1

    # 4. Insert new
    obs2 = [
        WeatherObservation(
            station_id="s1",
            ts=datetime(2025, 1, 1, 13, tzinfo=UTC),
            temperature_c=19.5,
            humidity_pct=50.0,
            wind_speed_ms=2.5,
            pressure_hpa=1014.1,
        )
    ]
    assert store.upsert(obs2) == 2
    assert store.count() == 2

    # 5. Read back
    read_obs = store.read(station_id="s1")
    assert len(read_obs) == 2
    assert read_obs[0].temperature_c == 21.0
    assert read_obs[1].temperature_c == 19.5
