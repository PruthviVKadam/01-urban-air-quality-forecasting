# plan.md — Urban Air Quality Forecasting

This is the build order. Each phase ends at a **gate** defined in `rules.md`. Do not start a phase until the previous gate is green. The goal at the end is a deployed, interactive, reliable web app — not a notebook.

---

## Phase 0 — Foundations & contracts

**Goal:** a runnable skeleton with the API contract pinned before any modeling.

- Scaffold `backend/` (FastAPI) and `frontend/` (Vite + React + TS + Tailwind) as separate, independently runnable apps.
- Define the **OpenAPI contract first**: endpoints `/stations`, `/forecast?station_id&horizon`, `/health`. Lock request/response schemas with Pydantic. Generate TypeScript types from the schema (e.g. `openapi-typescript`) so the front end can never drift from the back end.
- Stand up config via environment variables (`.env.example` committed, real `.env` git-ignored). No secrets in code.
- Add structured logging (JSON logs), a request-id middleware, and a `/health` endpoint returning data-freshness + last-refresh time.
- CI: lint (ruff + eslint), type-check (mypy + tsc), test runners wired even if empty.

**Exit gate:** G0 (Contract & CI) in `rules.md`.

## Phase 1 — Data ingestion (robust by construction)

**Goal:** a resilient ETL that never lets a bad upstream take down the app.

- Build ingestion clients for OpenAQ + AirNow (pollutants) and NOAA/Open-Meteo (weather). See `data-sources.md` for endpoints, keys, and rate limits.
- Every external call: timeout, retry with exponential backoff + jitter, and a circuit breaker. On hard failure, fall back to last-known-good cached data and mark it stale.
- Persist raw pulls to `data/raw/` (immutable) and cleaned series to `data/processed/`. Use a real store (SQLite/DuckDB or Parquet) — not in-memory only.
- **Data-quality validation** on every batch: schema check, range check (no negative PM₂.₅, plausible bounds), gap detection, duplicate-timestamp collapse. Quarantine bad rows; never silently drop.
- Missing values: interpolate only within documented limits AND tag every interpolated point with a boolean flag that survives all the way to the API payload.

**Exit gate:** G1 (Data Quality) in `rules.md`.

## Phase 2 — Features & baselines

**Goal:** honest baselines before any deep learning.

- Feature engineering: lags, rolling means/std, hour-of-day & day-of-week cyclical encodings, weather joins aligned per station, optional nearby-station augmentation for sparse sensors.
- Implement **two mandatory baselines**: persistence (next = last) and a seasonal/historical average. These are the bar every model must clear.
- Set up **walk-forward (rolling-origin) cross-validation**. No random k-fold on time series — ever.

**Exit gate:** baselines reproducible; CV harness committed.

## Phase 3 — Modeling

**Goal:** a forecasting model that measurably beats persistence per pollutant and horizon.

- Progression: ARIMA/SARIMAX → gradient-boosted trees on engineered features → LSTM/GRU (or Temporal Convolutional Net) for multivariate short-term forecasts.
- Track every run (params, metrics, data window) — MLflow or a simple committed CSV/JSON registry.
- Report MAE/RMSE per pollutant per horizon **and** exceedance-event classification metrics (precision/recall on "unhealthy" threshold crossings).
- Persist the chosen model + a model card (`models/MODEL_CARD.md`): training window, metrics vs baseline, known failure modes, refresh cadence.

**Exit gate:** G2 (Model-beats-baseline) in `rules.md`.

## Phase 4 — Serving API

**Goal:** the live backend the frontend consumes.

- FastAPI serves precomputed/cached forecasts; a scheduled job (APScheduler/cron) refreshes them. Inference is never blocking on a slow upstream during a user request.
- Responses include: predicted values, confidence interval, `interpolated` flags, `model_version`, `data_as_of`, and `beats_baseline` boolean.
- Add response caching + rate limiting on the API itself. Latency budget in `rules.md` (Hard Limit HL5).

**Exit gate:** G3 (API reliability + load smoke test).

## Phase 5 — Interactive frontend (the product)

**Goal:** the playground. See `DESIGN.md` for the full visual + interactivity spec.

Core interactive surfaces:

- **City map** (MapLibre): stations as living markers colored by current AQI; click to focus a station; hover for a quick read.
- **Horizon scrubber:** a slider/timeline the user drags to move the forecast 1→24h ahead and watch the map + charts recolor in real time.
- **Pollutant toggle:** switch PM₂.₅ / O₃ / NO₂ with an animated transition, not a page reload.
- **Forecast panel:** predicted-vs-actual time-series with the confidence band, the baseline line, and clear interpolation/stale markers.
- **"Play" timeline:** animate the next 24h so the city visibly breathes from clean to hazy.
- Every forecast surface shows the freshness timestamp and a model-vs-baseline badge — non-negotiable (HL1, HL2).

**Exit gate:** G4 (Accessibility + Interactivity) in `rules.md`.

## Phase 6 — Hardening & deploy

- End-to-end tests (Playwright) for the core interactions; backend integration tests against recorded fixtures.
- Error boundaries on every React route; skeleton/loading and explicit error states (never an infinite spinner).
- Dockerize backend + frontend; document one-command local run in `README`.
- Deploy (frontend static host + backend container). Smoke test the deployed URL.

**Exit gate:** G5 (Release readiness) — all gates green, deployed URL passes smoke test.

---

## Deliverables checklist

- [ ] Independently runnable `backend/` and `frontend/`, one-command dev start documented.
- [ ] Live API with freshness, CI bands, interpolation flags, model version.
- [ ] Model card showing it beats both baselines per pollutant/horizon.
- [ ] Interactive map explorer meeting the `DESIGN.md` motion + interactivity budget.
- [ ] Accessibility pass (color-blind-safe AQI, keyboard nav, reduced-motion).
- [ ] Tests (unit, integration, e2e) green in CI.
- [ ] Deployed URL + README with data-source links and license notes.
