"""Per-station, per-pollutant forecast endpoint.

In Phase 1, we still rely on the seed model logic (persistence baseline) to generate
the forecast shape, but we feed it the LIVE data from the ProcessedStore.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.aqi import aqi_for, category_from_aqi
from app.config import Settings, get_settings
from app.ingestion.station_registry import get_registry
from app.ingestion.storage import ProcessedStore, default_data_dir
from app.schemas import DataSource, ForecastResponse, LatestReading, Pollutant, Station
from app.seed import build_seed_forecast, get_seed_station, max_horizon_hours

router = APIRouter(tags=["forecast"])

def get_processed_store() -> ProcessedStore:
    return ProcessedStore(default_data_dir() / "processed" / "measurements.parquet")

@router.get("/forecast", response_model=ForecastResponse, summary="Forecast for a station")
def get_forecast(
    station_id: Annotated[str, Query(description="Station id from /stations.")],
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[ProcessedStore, Depends(get_processed_store)],
    pollutant: Annotated[Pollutant, Query(description="Pollutant to forecast.")] = Pollutant.pm25,
    horizon: Annotated[int, Query(ge=1, description="Hours ahead (1..max_horizon).")] = 24,
) -> ForecastResponse:
    horizon_cap = max_horizon_hours()
    if horizon > horizon_cap:
        raise HTTPException(
            status_code=422,
            detail=f"horizon {horizon}h exceeds the validated maximum of {horizon_cap}h",
        )
        
    registry = get_registry()
    seed_station = get_seed_station(station_id)
    
    # 1. Gather live station data
    station = None
    if station_id in registry:
        entry = registry[station_id]
        measurements = store.read(station_id=station_id)
        
        if measurements:
            latest_by_pol = {}
            for m in measurements:
                if m.pollutant not in latest_by_pol or m.ts > latest_by_pol[m.pollutant].ts:
                    latest_by_pol[m.pollutant] = m
                    
            if latest_by_pol:
                data_as_of = max(m.ts for m in latest_by_pol.values())
                is_stale = (datetime.now(UTC) - data_as_of) > timedelta(hours=settings.stale_threshold_hours)
                source = DataSource.cache if any(m.source == "cache" for m in latest_by_pol.values()) else DataSource.live
                
                readings = [
                    LatestReading(
                        pollutant=m.pollutant,
                        value=m.value,
                        unit=m.unit,
                        aqi=aqi_for(m.pollutant, m.value),
                        category=category_from_aqi(aqi_for(m.pollutant, m.value)),
                        interpolated=m.interpolated,
                        observed_at=m.ts,
                    )
                    for m in latest_by_pol.values()
                ]
                
                station = Station(
                    id=entry.station_id,
                    name=entry.name,
                    city=entry.city,
                    country=entry.country,
                    coordinates={"lat": entry.latitude, "lon": entry.longitude},
                    pollutants=entry.pollutants,
                    latest=readings,
                    data_as_of=data_as_of,
                    stale=is_stale,
                    data_source=source,
                )

    # 2. Fallback to seed if live data is completely missing
    if station is None:
        station = seed_station
        
    if station is None:
        raise HTTPException(status_code=404, detail=f"unknown station_id '{station_id}'")
        
    if pollutant not in station.pollutants:
        raise HTTPException(
            status_code=404, detail=f"station '{station_id}' does not report {pollutant.value}"
        )
        
    # Phase 1: still using seed model logic, but with real station/data_as_of metadata
    return build_seed_forecast(station, pollutant, horizon)
