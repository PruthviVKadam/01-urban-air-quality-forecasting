"""Integration tests for the ETL orchestrator."""

from datetime import UTC, datetime
from unittest.mock import patch

from app.ingestion.etl import run_etl
from app.ingestion.providers.base import ParseResult, WeatherObservation
from app.ingestion.providers.openaq import OpenAQClient
from app.ingestion.providers.open_meteo import OpenMeteoClient
from app.ingestion.providers.airnow import AirNowClient
from app.ingestion.models import Measurement
from app.schemas import Pollutant
from app.ingestion.resilient_client import FetchResult

def test_etl_orchestrator(tmp_path) -> None:
    # Patch default data dir so we use tmp_path
    with patch("app.ingestion.etl.default_data_dir", return_value=tmp_path):
        
        # Mock the registry to have only one station to speed up test
        mock_registry = {
            "us-nyc-cp": __import__("app.ingestion.station_registry", fromlist=["StationEntry"]).StationEntry(
                station_id="us-nyc-cp",
                name="Central Park",
                city="New York",
                country="US",
                latitude=40.7829,
                longitude=-73.9654,
                sensors=[
                    __import__("app.ingestion.station_registry", fromlist=["SensorMapping"]).SensorMapping(Pollutant.pm25, 3550)
                ]
            )
        }
        
        # Mock the provider clients
        with patch("app.ingestion.etl.get_registry", return_value=mock_registry), \
             patch.object(OpenAQClient, "fetch_measurements") as mock_openaq, \
             patch.object(OpenMeteoClient, "fetch_weather") as mock_openmeteo, \
             patch.object(AirNowClient, "fetch_current") as mock_airnow:
             
            # 1. Setup mock OpenAQ measurements (some good, some out-of-bounds, a gap)
            ts1 = datetime(2025, 1, 1, 10, tzinfo=UTC)
            ts2 = datetime(2025, 1, 1, 12, tzinfo=UTC) # 1 hour gap
            bad_ts = datetime(2025, 1, 1, 13, tzinfo=UTC) # Out of bounds
            
            good_m1 = Measurement(station_id="us-nyc-cp", pollutant=Pollutant.pm25, ts=ts1, value=15.0, unit="µg/m³", source="openaq")
            good_m2 = Measurement(station_id="us-nyc-cp", pollutant=Pollutant.pm25, ts=ts2, value=18.0, unit="µg/m³", source="openaq")
            bad_m = Measurement(station_id="us-nyc-cp", pollutant=Pollutant.pm25, ts=bad_ts, value=-5.0, unit="µg/m³", source="openaq") # negative, will be quarantined
            
            mock_openaq.return_value = (FetchResult({}, False, False), ParseResult([good_m1, good_m2, bad_m], 0))
            
            # 2. Setup mock Open-Meteo weather
            w1 = WeatherObservation(station_id="us-nyc-cp", ts=ts1, temperature_c=10.0, humidity_pct=50.0, wind_speed_ms=2.0, pressure_hpa=1010.0)
            mock_openmeteo.return_value = (FetchResult({}, False, False), [w1])
            
            # 3. Setup mock AirNow current
            mock_airnow.return_value = (FetchResult({}, False, False), [])
            
            since = datetime(2025, 1, 1, 0, tzinfo=UTC)
            until = datetime(2025, 1, 1, 23, tzinfo=UTC)
            
            report = run_etl(since, until)
            
            # Assertions
            sr = report.stations["us-nyc-cp"]
            assert sr.fetched == 3
            assert sr.quarantined == 1 # The negative value
            assert sr.gaps_found == 1 # The 1 hour gap between 10:00 and 12:00
            assert sr.interpolated == 1 # Gap should be filled
            assert sr.accepted == 3 # 2 good + 1 interpolated
            assert sr.weather_fetched == 1
            
            # Verify the output stores
            from app.ingestion.storage import ProcessedStore, QuarantineStore
            processed = ProcessedStore(tmp_path / "processed" / "measurements.parquet")
            quarantine = QuarantineStore(tmp_path / "processed" / "quarantine.parquet")
            
            assert processed.count() == 3
            assert quarantine.count() == 1
            
            # Verify interpolated flag
            readings = processed.read(station_id="us-nyc-cp", pollutant=Pollutant.pm25)
            # They should be sorted by ts
            assert readings[0].ts == ts1
            assert not readings[0].interpolated
            
            assert readings[1].ts == datetime(2025, 1, 1, 11, tzinfo=UTC)
            assert readings[1].interpolated
            assert readings[1].value == 16.5 # (15 + 18) / 2
            
            assert readings[2].ts == ts2
            assert not readings[2].interpolated
