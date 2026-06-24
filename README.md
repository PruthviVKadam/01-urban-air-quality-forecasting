# Atmosphere — Urban Air Quality Forecasting

A living, reliability-first urban air-quality forecast explorer.

Atmosphere forecasts PM₂.₅, O₃, and NO₂ levels across global cities up to 24 hours into the future. It is built to demonstrate what a highly resilient, data-honest, and interactive AI application looks like — failing soft when public APIs go dark, surfacing its own baseline confidence metrics, and prioritizing user experience with 60fps scrubbing animations.

## Architecture

1. **ETL Pipeline**: An idempotent ingest job pulling live telemetry from OpenAQ, US EPA AirNow, and Open-Meteo. Data is cleaned, imputed, and stored in a local DuckDB data warehouse.
2. **Machine Learning**: A `HistGradientBoostingRegressor` trained via walk-forward cross-validation. It natively handles missing features and generates robust 95% confidence intervals.
3. **Serving API**: A high-performance FastAPI endpoint equipped with an in-memory TTL cache and sliding-window rate limit, ensuring <800ms latencies and zero downtime.
4. **Interactive Visualization**: A React + MapLibre GL JS frontend featuring a dynamic 24h timeline scrubber. 

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
uv run uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm run dev
```

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
