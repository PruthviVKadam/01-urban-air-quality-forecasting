# Atmosphere · Urban Air Quality Forecasting

A reliability-first web app that forecasts the next 6–24 hours of urban air quality
(PM₂.₅, O₃, NO₂) per monitoring station and presents it as an **interactive, living
city explorer** — not a notebook dump. Built on a typed, contract-first API where the
frontend can never drift from the backend.

> **Status: Phase 0 (Foundations) complete.** The OpenAPI contract, the resilient
> backend shell, and the typed, on-brand frontend shell are wired and green in CI. The
> live data pipeline (Phase 1) and forecasting model (Phase 3) replace the clearly
> labeled **seed** data that Phase 0 serves. See [`plan.md`](plan.md) for the phase plan.

## Why it's built this way

This app consumes flaky public sensor feeds, so robustness is designed in from line one
(see [`rules.md`](rules.md) for the full hard-limit list):

- **Freshness is mandatory (HL1).** Nothing renders without a `data_as_of` timestamp;
  data older than 3 hours is flagged stale, in the payload and the UI.
- **No model without a baseline shadow (HL2).** Every forecast ships the persistence
  baseline and a `beats_baseline` flag; a model that can't beat persistence can't ship.
- **No silent imputation (HL3).** Interpolated points carry an `interpolated` flag from
  ETL → API → UI and are drawn distinctly.
- **Not medical advice (HL4).** AQI category + EPA descriptor only, with a persistent
  disclaimer.
- **Latency & resilience budget (HL5).** Cached responses; external calls get timeouts,
  retries with backoff, and circuit breakers; upstream failure degrades to last-known-good.

## Architecture

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite + TypeScript + Tailwind v4 (custom *Atmosphere* design tokens) |
| Backend | FastAPI (Python 3.12) serving a typed REST API |
| Contract | OpenAPI schema is the source of truth; TS types are generated from it |
| ML (later) | pandas · statsmodels · LightGBM/XGBoost · PyTorch (LSTM/GRU) |

The backend's Pydantic schemas *are* the contract: `backend/scripts/export_openapi.py`
writes [`backend/openapi.json`](backend/openapi.json), and the frontend runs
`openapi-typescript` against it (`npm run gen:types`). CI fails if either drifts.

## Run it locally

Prerequisites: [uv](https://docs.astral.sh/uv/) and Node 20+.

```bash
# 1) Backend — http://127.0.0.1:8000  (interactive docs at /docs)
cd backend
uv sync
uv run uvicorn app.main:app --reload

# 2) Frontend — http://localhost:5173  (in a second terminal)
cd frontend
npm install
npm run gen:types        # generate TS types from the backend contract
npm run dev
```

No API keys are needed in Phase 0. For later phases, copy `backend/.env.example` to
`backend/.env` and fill in free-tier keys; `.env` is gitignored.

## Checks

```bash
# backend
cd backend && uv run ruff check . && uv run mypy app && uv run pytest
# frontend
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build
```

## Project layout

```
backend/    FastAPI app, OpenAPI contract, seed provider, tests
frontend/   Vite + React + TS app, typed API client, Atmosphere design system
data/       raw/ + processed/ (gitignored; populated by the Phase 1 ETL)
models/     model card + registry (weights gitignored)
notebooks/  exploration (Phase 2+)
```

## Data sources & licenses

| Source | Use | License / terms |
|--------|-----|-----------------|
| [OpenAQ](https://docs.openaq.org/) | Pollutant measurements | Open data, CC BY 4.0 (attribute OpenAQ + providers) |
| [US EPA AirNow](https://docs.airnowapi.org/) | Official US AQI + descriptors | US Government data; AirNow data-use guidelines |
| [Open-Meteo](https://open-meteo.com/) | Weather (exogenous features) | CC BY 4.0; no key required |

See [`data-sources.md`](data-sources.md) for endpoints, rate limits, and failure behavior.

## Documentation

- [`plan.md`](plan.md) — phased build order and gates
- [`rules.md`](rules.md) — hard limits and gating checkpoints
- [`DESIGN.md`](DESIGN.md) — visual system, anti-slop checklist, interactivity spec
- [`data-sources.md`](data-sources.md) — datasets, licenses, rate limits
