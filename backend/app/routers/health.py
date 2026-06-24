"""Liveness + freshness probe. Reports uptime, last refresh, and upstream status."""

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app import __version__
from app.config import PROVIDERS
from app.schemas import HealthResponse, ProviderHealth, UpstreamStatus

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, summary="Liveness and data freshness")
def health(request: Request) -> HealthResponse:
    start: float = request.app.state.start_time
    # Phase 0: no ETL yet, so upstream status is 'unknown' and last_refresh is null.
    upstreams = [
        ProviderHealth(name=cfg.name, status=UpstreamStatus.unknown) for cfg in PROVIDERS.values()
    ]
    return HealthResponse(
        status="ok",
        version=__version__,
        time=datetime.now(UTC),
        uptime_seconds=round(time.monotonic() - start, 3),
        last_refresh=None,
        data_as_of=None,
        upstreams=upstreams,
        cache_hit_rate=None,
    )
