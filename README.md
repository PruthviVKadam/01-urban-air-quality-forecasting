# Atmosphere — Urban Air Quality Forecasting

A living, reliability-first urban air-quality forecast explorer.

Atmosphere forecasts PM₂.₅, O₃, and NO₂ levels across global cities up to 24 hours into the future. It is built to demonstrate what a highly resilient, data-honest, and interactive AI application looks like — failing soft when public APIs go dark, surfacing its own baseline confidence metrics, and prioritizing user experience with 60fps scrubbing animations.

## Architecture

1. **ETL Pipeline**: An idempotent ingest job pulling live telemetry from OpenAQ, US EPA AirNow, and Open-Meteo. Data is cleaned, imputed, and stored in a local DuckDB data warehouse.
2. **Machine Learning**: Per-pollutant, per-horizon `HistGradientBoostingRegressor` models (direct multi-step) that predict the *change from the current value*, scored by walk-forward (rolling-origin) cross-validation against persistence **and** seasonal-average baselines. A model is promoted to production **only** for a pollutant it beats at every horizon (see [Reported results](#reported-results-reproducible)); `beats_baseline` is read from the committed evaluation, never hardcoded (HL2).
3. **Serving API**: A high-performance FastAPI endpoint equipped with an in-memory TTL cache and sliding-window rate limit, ensuring <800ms latencies and zero downtime.
4. **Interactive Visualization**: A React + MapLibre GL JS frontend featuring a dynamic 24h timeline scrubber.

## Reported results (reproducible)

The repo ships a **deterministic synthetic backfill** (`app/modeling/synthetic.py`) so the
full modeling story — 45 days × 5 stations of hourly data, data-quality validation, and the
model-vs-baseline evaluation — reproduces on any machine without paid API keys. The synthetic
bytes are pushed through the *same* validation → quarantine → interpolation → feature pipeline
as live data, so gate G1 is genuinely exercised (an injected bad batch is quarantined; short
gaps are interpolated and flagged, long gaps are left as gaps). Walk-forward CV then certifies
each pollutant independently:

| Pollutant | Model MAE | Persistence MAE | Seasonal MAE | Beats both at every horizon? |
| --------- | --------- | --------------- | ------------ | ---------------------------- |
| O₃ | **2.81** | 10.10 | 5.00 | ✅ certified — served by the model |
| NO₂ | **6.25** | 11.25 | 9.57 | ✅ certified — served by the model |
| PM₂.₅ | **6.25** | 10.70 | 9.16 | ❌ at parity on the 24h echo — served as persistence |

> Certification requires beating **both** baselines on **both** MAE and RMSE by a meaningful
> margin at **every** horizon (1–24h). PM₂.₅ wins comfortably on the aggregate but only ties
> persistence at the 24-hour "same hour yesterday" echo, so — honoring HL2 — it is **not**
> promoted: the API serves its persistence forecast with `beats_baseline=false`. Numbers come
> from `scripts/seed_and_train.py` and are committed in [`models/registry.json`](models/registry.json)
> and [`models/MODEL_CARD.md`](models/MODEL_CARD.md). Re-run on a real point-in-time pull to
> re-certify; the contract, features, and evaluation are unchanged.

## Run Locally (One-Command Start)

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

```bash
# Start the backend API on port 8000 and frontend UI on port 80
docker compose up --build
```

Open `http://localhost` in your browser.

> **Note on Initial Boot:** The first time the backend boots, it will spin up the ETL pipeline to fetch 30 days of historical data and train the ML models. This may take a minute. If you open the UI before this finishes, you will see a graceful "Stale/Baseline" state per our reliability mandates.

### Running for Development

If you wish to run the app natively without Docker:

**Terminal 1 (Backend):**

```bash
cd backend
uv sync
uv run python -m scripts.seed_and_train   # build the reproducible dataset, train + certify models
uv run uvicorn app.main:app --reload
```

`seed_and_train` is deterministic — it regenerates `data/features/features.parquet`,
`models/registry.json`, and `models/MODEL_CARD.md` identically on every run. (The
multi-megabyte model weights it writes under `models/` are gitignored; the committed
registry + card are the evidence.) Without it, the API still runs and degrades honestly to
the seed/persistence forecast.

**Terminal 2 (Frontend):**

```bash
cd frontend
npm install
npm run dev
```

**Checks:** `cd backend && uv run ruff check . && uv run mypy app tests && uv run pytest` ·
`cd frontend && npm run lint && npm run typecheck && npm run build`

## Data Sources & Licenses

This project consumes public data under the following licenses:

- **OpenAQ**: CC BY 4.0
- **US EPA AirNow**: Public Domain (US Government Work)
- **Open-Meteo**: CC BY 4.0

## Reliability Mandates (Hard Limits)

This application enforces strict architectural rules (`rules.md`):

- **HL1:** Freshness is mandatory (`data_as_of` attached everywhere).
- **HL2:** No model without a baseline shadow (we always test against persistence).
- **HL3:** No silent imputation (interpolated flags flow from ETL to UI).
- **HL5:** API Latency budget < 800ms.
