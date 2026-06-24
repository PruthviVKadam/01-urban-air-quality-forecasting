"""Per-station, per-pollutant forecast endpoint (seed data in Phase 0)."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ForecastResponse, Pollutant
from app.seed import build_seed_forecast, get_seed_station, max_horizon_hours

router = APIRouter(tags=["forecast"])


@router.get("/forecast", response_model=ForecastResponse, summary="Forecast for a station")
def get_forecast(
    station_id: Annotated[str, Query(description="Station id from /stations.")],
    pollutant: Annotated[Pollutant, Query(description="Pollutant to forecast.")] = Pollutant.pm25,
    horizon: Annotated[int, Query(ge=1, description="Hours ahead (1..max_horizon).")] = 24,
) -> ForecastResponse:
    horizon_cap = max_horizon_hours()
    if horizon > horizon_cap:
        raise HTTPException(
            status_code=422,
            detail=f"horizon {horizon}h exceeds the validated maximum of {horizon_cap}h",
        )
    station = get_seed_station(station_id)
    if station is None:
        raise HTTPException(status_code=404, detail=f"unknown station_id '{station_id}'")
    if pollutant not in station.pollutants:
        raise HTTPException(
            status_code=404, detail=f"station '{station_id}' does not report {pollutant.value}"
        )
    return build_seed_forecast(station, pollutant, horizon)
