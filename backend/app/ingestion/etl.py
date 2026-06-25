"""ETL orchestrator — ties providers → validation → interpolation → storage.

Runs the full data pipeline. Handles per-station failures independently (a single
offline sensor never blanks the map).
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.config import get_settings
from app.ingestion.interpolation import interpolate_series
from app.ingestion.providers import (
    AirNowClient,
    OpenAQClient,
    OpenMeteoClient,
    build_client,
    resolve_api_key,
)
from app.ingestion.station_registry import get_registry
from app.ingestion.storage import (
    ProcessedStore,
    QuarantineStore,
    RawStore,
    default_data_dir,
)
from app.ingestion.validation import validate_batch
from app.ingestion.weather_store import WeatherStore

logger = logging.getLogger("uaqf.ingestion.etl")


@dataclass
class StationReport:
    fetched: int = 0
    accepted: int = 0
    quarantined: int = 0
    interpolated: int = 0
    gaps_found: int = 0
    weather_fetched: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class IngestionReport:
    start_time: datetime
    end_time: datetime | None = None
    stations: dict[str, StationReport] = field(default_factory=dict)

    @property
    def duration_s(self) -> float:
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()


def run_etl(since: datetime, until: datetime) -> IngestionReport:
    """Run the ingestion pipeline for a given time window."""
    settings = get_settings()
    data_dir = default_data_dir()
    cache_dir = data_dir / "cache"

    raw_store = RawStore(data_dir / "raw")
    processed_store = ProcessedStore(data_dir / "processed" / "measurements.parquet")
    quarantine_store = QuarantineStore(data_dir / "processed" / "quarantine.parquet")
    weather_store = WeatherStore(data_dir / "processed" / "weather.parquet")

    report = IngestionReport(start_time=datetime.now(UTC))

    # Initialize clients with resilient wrapper (circuit breakers, cache, retries)
    with (
        build_client("openaq", cache_dir, settings) as openaq_http,
        build_client("open-meteo", cache_dir, settings) as openmeteo_http,
        build_client("airnow", cache_dir, settings) as airnow_http,
    ):
        openaq_client = OpenAQClient(openaq_http, resolve_api_key("openaq", settings))
        openmeteo_client = OpenMeteoClient(openmeteo_http)
        airnow_client = AirNowClient(airnow_http, resolve_api_key("airnow", settings))

        registry = get_registry()

        for station_id, entry in registry.items():
            station_report = StationReport()
            report.stations[station_id] = station_report

            all_measurements = []

            # 1. Fetch from OpenAQ (measurements)
            for sensor in entry.sensors:
                try:
                    fetch_res, parse_res = openaq_client.fetch_measurements(
                        sensor.sensor_id,
                        station_id=station_id,
                        date_from=since,
                        date_to=until,
                    )
                    raw_store.write_raw(
                        "openaq",
                        station_id,
                        f"sensor_{sensor.sensor_id}",
                        fetch_res.data,
                    )
                    all_measurements.extend(parse_res.measurements)
                    station_report.fetched += len(parse_res.measurements)
                except Exception as e:
                    logger.warning(
                        "openaq_fetch_failed", extra={"station": station_id, "error": str(e)}
                    )
                    station_report.errors.append(f"OpenAQ {sensor.pollutant.value}: {e}")

            # 2. Fetch from Open-Meteo (weather features)
            try:
                # Approximate days needed based on since/until
                now = datetime.now(UTC)
                past_days = max(2, (now - since).days + 1)
                forecast_days = max(2, (until - now).days + 1) if until > now else 0

                fetch_res, weather_obs = openmeteo_client.fetch_weather(
                    entry.latitude,
                    entry.longitude,
                    station_id=station_id,
                    past_days=past_days,
                    forecast_days=forecast_days,
                )
                raw_store.write_raw("open-meteo", station_id, "forecast", fetch_res.data)

                # Filter strictly to our window
                weather_obs = [o for o in weather_obs if since <= o.ts <= until]

                weather_store.upsert(weather_obs)
                station_report.weather_fetched += len(weather_obs)
            except Exception as e:
                logger.warning(
                    "openmeteo_fetch_failed", extra={"station": station_id, "error": str(e)}
                )
                station_report.errors.append(f"Open-Meteo: {e}")

            # 3. AirNow Enrichment (optional)
            # This fetches current data. We run it to ensure it is cached/tested,
            # and could merge it with latest measurements.
            try:
                fetch_res, _airnow_obs = airnow_client.fetch_current(
                    entry.latitude, entry.longitude, station_id=station_id
                )
                raw_store.write_raw("airnow", station_id, "current", fetch_res.data)
                # AirNow is enrichment for category. In Phase 1 we just test the fetch.
            except Exception as e:
                logger.info("airnow_fetch_failed", extra={"station": station_id, "error": str(e)})
                # Do not count AirNow failure as a hard error for the station

            # 4. Validate Measurements
            if all_measurements:
                val_report = validate_batch(all_measurements)
                station_report.quarantined = val_report.quarantined_count
                station_report.gaps_found = len(val_report.gaps)

                if val_report.quarantined_count > 0:
                    quarantine_store.append(val_report.quarantined)

                # 5. Interpolate (with flags)
                interpolated_series = interpolate_series(val_report.accepted)

                # Count newly added points by comparing lengths
                station_report.interpolated = len(interpolated_series) - len(val_report.accepted)
                station_report.accepted = len(interpolated_series)

                # 6. Upsert to ProcessedStore
                processed_store.upsert(interpolated_series)

    # 7. Update ML Features
    try:
        from app.modeling.features import build_features

        build_features(data_dir)
        logger.info("features_rebuilt")
    except Exception as e:
        logger.error("features_rebuild_failed", extra={"error": str(e)})

    report.end_time = datetime.now(UTC)

    logger.info(
        "etl_completed",
        extra={
            "duration_s": round(report.duration_s, 2),
            "stations_processed": len(registry),
        },
    )
    return report
