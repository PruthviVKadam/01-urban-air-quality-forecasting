"""Monitoring stations + their latest readings.

In Phase 1, we pull the latest measurements from the ProcessedStore. If no data exists
yet, we fall back to the Phase 0 seed data. Stale flags are computed dynamically based
on the config threshold (HL1).
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends

from app.aqi import aqi_for, category_from_aqi
from app.config import Settings, get_settings
from app.ingestion.station_registry import get_registry
from app.ingestion.storage import ProcessedStore, default_data_dir
from app.schemas import DataSource, LatestReading, Station
from app.seed import get_seed_stations

router = APIRouter(tags=["stations"])

def get_processed_store() -> ProcessedStore:
    return ProcessedStore(default_data_dir() / "processed" / "measurements.parquet")

@router.get("/stations", response_model=list[Station], summary="List monitoring stations")
def list_stations(
    settings: Annotated[Settings, Depends(get_settings)],
    store: Annotated[ProcessedStore, Depends(get_processed_store)]
) -> list[Station]:
    
    registry = get_registry()
    seed_stations = {s.id: s for s in get_seed_stations()}
    stations: list[Station] = []
    
    now = datetime.now(UTC)
    
    for station_id, entry in registry.items():
        # Fallback to seed if not in registry? Registry has all seed stations.
        measurements = store.read(station_id=station_id)
        
        if not measurements:
            # Fall back to seed
            if station_id in seed_stations:
                stations.append(seed_stations[station_id])
            continue
            
        # Group by pollutant to find the latest
        latest_by_pol = {}
        for m in measurements:
            if m.pollutant not in latest_by_pol or m.ts > latest_by_pol[m.pollutant].ts:
                latest_by_pol[m.pollutant] = m
                
        if not latest_by_pol:
            if station_id in seed_stations:
                stations.append(seed_stations[station_id])
            continue
            
        # Overall data_as_of is the newest timestamp among the latest readings
        data_as_of = max(m.ts for m in latest_by_pol.values())
        is_stale = (now - data_as_of) > timedelta(hours=settings.stale_threshold_hours)
        
        # Check source — if any reading came from cache, label the station as cache
        source = DataSource.live
        for m in latest_by_pol.values():
            if m.source == "cache":
                source = DataSource.cache
                break
                
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
        stations.append(station)
        
    return stations
