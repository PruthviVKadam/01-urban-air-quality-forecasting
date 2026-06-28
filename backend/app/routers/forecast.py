"""Per-station, per-pollutant forecast endpoint.

Serves cached forecasts from the latest stored features (never blocking on a live upstream
— HL5). A certified ML model is used only for pollutants the committed evaluation proved
beat both baselines (HL2); everything else degrades to the honest persistence forecast. The
freshness timestamp, stale flag, interpolation flags, and baseline shadow ride on every
response so the UI can never render a number without its provenance.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.aqi import aqi_for, category_from_aqi
from app.cache import ttl_cache
from app.config import Settings, get_settings
from app.constants import DISCLAIMER
from app.ingestion.models import Measurement
from app.ingestion.station_registry import get_registry
from app.ingestion.storage import ProcessedStore, default_data_dir
from app.schemas import (
    DataSource,
    ForecastPoint,
    ForecastResponse,
    LatestReading,
    Pollutant,
    Station,
)
from app.seed import build_seed_forecast, get_seed_station, max_horizon_hours

router = APIRouter(tags=["forecast"])


def get_processed_store() -> ProcessedStore:
    return ProcessedStore(default_data_dir() / "processed" / "measurements.parquet")


@router.get("/forecast", response_model=ForecastResponse, summary="Forecast for a station")
@ttl_cache(ttl_seconds=300)
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
            latest_by_pol: dict[Pollutant, Measurement] = {}
            for m in measurements:
                if m.pollutant not in latest_by_pol or m.ts > latest_by_pol[m.pollutant].ts:
                    latest_by_pol[m.pollutant] = m

            if latest_by_pol:
                data_as_of = max(m.ts for m in latest_by_pol.values())
                is_stale = (datetime.now(UTC) - data_as_of) > timedelta(
                    hours=settings.stale_threshold_hours
                )
                source = (
                    DataSource.cache
                    if any(m.source == "cache" for m in latest_by_pol.values())
                    else DataSource.live
                )

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

    # Phase 4: serving-layer inference.
    #
    # HL2 is enforced structurally here: the ML model is served *only* for a pollutant the
    # committed walk-forward evaluation certified as beating both baselines at every horizon
    # (``registry.json`` → ``beats_baseline``). For any other pollutant — or if the model or
    # features are unavailable — we fall back to the honest persistence forecast with
    # ``beats_baseline=False``. ``beats_baseline`` is *read*, never asserted, so a model that
    # does not beat persistence can never reach production claiming that it does.
    import logging

    logger = logging.getLogger("uaqf.forecast")

    try:
        from app.modeling.inference import get_inference_engine

        engine = get_inference_engine()
        if not (engine.has_model(pollutant) and engine.beats_baseline(pollutant)):
            return build_seed_forecast(station, pollutant, horizon)

        ml_preds = engine.predict(station_id, pollutant, horizon)
        persistence_val = station.latest[0].value if station.latest else 0.0
        forecast_points = [
            ForecastPoint(
                ts=ts,
                value=val,
                lower=lower,
                upper=upper,
                baseline=persistence_val,  # HL2 — persistence shadow on every point
                aqi=aqi_for(pollutant, val),
                category=category_from_aqi(aqi_for(pollutant, val)),
                interpolated=station.latest[0].interpolated if station.latest else False,
            )
            for ts, val, lower, upper in ml_preds
        ]
    except Exception as e:
        logger.warning("inference_fallback", extra={"station": station_id, "error": str(e)})
        return build_seed_forecast(station, pollutant, horizon)

    return ForecastResponse(
        station_id=station.id,
        station_name=station.name,
        pollutant=pollutant,
        unit=station.latest[0].unit if station.latest else "",
        horizon_hours=horizon,
        generated_at=datetime.now(UTC),
        data_as_of=station.data_as_of,
        stale=station.stale,
        data_source=station.data_source,
        model_version=engine.model_version(pollutant),
        baseline_label="persistence",
        beats_baseline=engine.beats_baseline(pollutant),
        disclaimer=DISCLAIMER,
        points=forecast_points,
    )
