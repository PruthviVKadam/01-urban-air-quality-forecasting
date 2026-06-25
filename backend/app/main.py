"""FastAPI application entrypoint: middleware, uniform error envelope, routers."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import get_settings
from app.ingestion.etl import run_etl
from app.logging_config import configure_logging
from app.middleware import RateLimitMiddleware, RequestIdMiddleware
from app.request_context import get_request_id
from app.routers import forecast, health, stations
from app.schemas import ErrorResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("uaqf")


async def _ingestion_loop() -> None:
    # Brief initial delay so the app responds to /health immediately
    await asyncio.sleep(5)
    while True:
        try:
            logger.info(
                "ingestion_starting", extra={"lookback_hours": settings.ingestion_lookback_hours}
            )
            now = datetime.now(UTC)
            since = now - timedelta(hours=settings.ingestion_lookback_hours)

            # run_etl is synchronous, run it in a thread
            report = await asyncio.to_thread(run_etl, since, now)

            # Save latest refresh details on app state
            app.state.last_refresh = report.end_time
            app.state.last_ingestion_report = report

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("ingestion_failed_unexpectedly", extra={"error": str(e)})

        # Wait for next interval
        await asyncio.sleep(settings.ingestion_interval_minutes * 60)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.start_time = time.monotonic()
    app.state.last_refresh = None
    app.state.last_ingestion_report = None

    logger.info("startup", extra={"app_env": settings.app_env, "version": __version__})

    task = None
    if settings.ingestion_enabled:
        task = asyncio.create_task(_ingestion_loop())

    yield

    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    logger.info("shutdown")


app = FastAPI(
    title="Urban Air Quality Forecasting API",
    version=__version__,
    summary="Live, reliability-first air-quality forecasts with baseline + freshness honesty.",
    description=(
        "Contract-first API. Every forecast carries a freshness timestamp (HL1), a "
        "persistence baseline + beats_baseline flag (HL2), per-point interpolation flags "
        "(HL3), and a not-medical-guidance disclaimer (HL4)."
    ),
    lifespan=lifespan,
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _error(status_code: int, error: str, code: str, detail: str | None) -> JSONResponse:
    body = ErrorResponse(error=error, code=code, detail=detail, request_id=get_request_id())
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(422, "validation_error", "validation_error", str(exc.errors()))


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = "not_found" if exc.status_code == 404 else f"http_{exc.status_code}"
    return _error(exc.status_code, "request_error", code, str(exc.detail))


@app.exception_handler(Exception)
async def on_unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    # HL5 — never leak internals; log the detail, return a generic envelope.
    logger.exception("unhandled_error", extra={"path": request.url.path})
    return _error(500, "internal_error", "internal_error", "An unexpected error occurred.")


app.include_router(health.router)
app.include_router(stations.router)
app.include_router(forecast.router)
