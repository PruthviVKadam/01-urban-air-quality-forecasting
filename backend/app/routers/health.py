"""Liveness + freshness probe. Reports uptime, last refresh, and upstream status."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from app import __version__
from app.config import PROVIDERS
from app.ingestion.storage import ProcessedStore, default_data_dir
from app.schemas import HealthResponse, ProviderHealth, UpstreamStatus

router = APIRouter(tags=["system"])


def get_processed_store() -> ProcessedStore:
    return ProcessedStore(default_data_dir() / "processed" / "measurements.parquet")


@router.get("/health", response_model=HealthResponse, summary="Liveness and data freshness")
def health(
    request: Request, store: ProcessedStore = Depends(get_processed_store)  # noqa: B008
) -> HealthResponse:
    start: float = request.app.state.start_time
    last_refresh = getattr(request.app.state, "last_refresh", None)

    # In Phase 1, we don't have circuit breaker state exposed globally.
    # We report the status from the latest ingestion report if available.
    last_report = getattr(request.app.state, "last_ingestion_report", None)

    upstreams = []
    for key, cfg in PROVIDERS.items():
        status = UpstreamStatus.unknown
        if last_report:
            # Check if any station had errors for this provider
            has_error = any(
                any(key.lower() in err.lower() for err in s_report.errors)
                for s_report in last_report.stations.values()
            )
            status = UpstreamStatus.down if has_error else UpstreamStatus.ok

        upstreams.append(ProviderHealth(name=cfg.name, status=status))

    # Get data_as_of from the processed store
    data_as_of = store.get_latest_ts()

    return HealthResponse(
        status="ok",
        version=__version__,
        time=datetime.now(UTC),
        uptime_seconds=round(time.monotonic() - start, 3),
        last_refresh=last_refresh,
        data_as_of=data_as_of,
        upstreams=upstreams,
        cache_hit_rate=None,  # Cache hit rate not implemented yet
    )
