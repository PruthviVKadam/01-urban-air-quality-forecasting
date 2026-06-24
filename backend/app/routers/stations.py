"""Monitoring stations + their latest readings (seed data in Phase 0)."""

from fastapi import APIRouter

from app.schemas import Station
from app.seed import get_seed_stations

router = APIRouter(tags=["stations"])


@router.get("/stations", response_model=list[Station], summary="List monitoring stations")
def list_stations() -> list[Station]:
    return get_seed_stations()
