"""Tests for feature engineering pipeline."""

from datetime import UTC, datetime
from pathlib import Path

import duckdb
from app.ingestion.models import Measurement
from app.ingestion.providers.base import WeatherObservation
from app.ingestion.storage import ProcessedStore
from app.ingestion.weather_store import WeatherStore
from app.modeling.features import build_features
from app.schemas import Pollutant


def test_build_features(tmp_path: Path) -> None:
    # 1. Setup processed data
    processed_dir = tmp_path / "processed"
    measurements_store = ProcessedStore(processed_dir / "measurements.parquet")
    weather_store = WeatherStore(processed_dir / "weather.parquet")

    ts1 = datetime(2025, 1, 1, 10, tzinfo=UTC)
    ts2 = datetime(2025, 1, 1, 11, tzinfo=UTC)

    # Insert measurements (LONG format)
    measurements_store.upsert(
        [
            Measurement(
                station_id="s1", pollutant=Pollutant.pm25, ts=ts1, value=10.0, unit="µg", source="m"
            ),
            Measurement(
                station_id="s1", pollutant=Pollutant.o3, ts=ts1, value=20.0, unit="ppb", source="m"
            ),
            Measurement(
                station_id="s1", pollutant=Pollutant.pm25, ts=ts2, value=15.0, unit="µg", source="m"
            ),
        ]
    )

    # Insert weather
    weather_store.upsert(
        [
            WeatherObservation(
                station_id="s1",
                ts=ts1,
                temperature_c=15.0,
                humidity_pct=50.0,
                wind_speed_ms=2.0,
                pressure_hpa=1010.0,
            ),
            WeatherObservation(
                station_id="s1",
                ts=ts2,
                temperature_c=16.0,
                humidity_pct=48.0,
                wind_speed_ms=2.5,
                pressure_hpa=1009.0,
            ),
        ]
    )

    # 2. Build features
    features_path = build_features(tmp_path)

    assert features_path.exists()

    # 3. Verify output
    con = duckdb.connect()
    try:
        df = con.execute(
            f"SELECT * FROM read_parquet('{features_path.as_posix()}') ORDER BY ts"
        ).df()

        assert len(df) == 2

        # Verify wide format
        assert df.iloc[0]["pm25"] == 10.0
        assert df.iloc[0]["o3"] == 20.0
        # no2 should be NaN/None since we didn't insert it
        import math

        assert math.isnan(df.iloc[0]["no2"])

        # Verify weather join
        assert df.iloc[0]["temperature_c"] == 15.0
        assert df.iloc[1]["temperature_c"] == 16.0

        # Verify lags and rolling
        assert math.isnan(df.iloc[0]["pm25_lag_1h"])  # first row
        assert df.iloc[1]["pm25_lag_1h"] == 10.0  # second row sees first row

        assert df.iloc[0]["pm25_roll_mean_24h"] == 10.0
        assert df.iloc[1]["pm25_roll_mean_24h"] == 12.5  # (10 + 15) / 2

        # Verify cyclical features
        assert df.iloc[0]["hour_of_day"] == 10
        # sin(10 * pi / 12) = sin(5pi/6) = 0.5
        assert round(df.iloc[0]["sin_hour"], 4) == 0.5
    finally:
        con.close()
