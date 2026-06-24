"""FastAPI application entrypoint: middleware, uniform error envelope, routers."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestIdMiddleware
from app.request_context import get_request_id
from app.routers import forecast, health, stations
from app.schemas import ErrorResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("uaqf")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.start_time = time.monotonic()
    logger.info("startup", extra={"app_env": settings.app_env, "version": __version__})
    yield
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

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


def _error(status_code: int, error: str, code: str, detail: str | None) -> JSONResponse:
    body = ErrorResponse(
        error=error, code=code, detail=detail, request_id=get_request_id()
    )
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
