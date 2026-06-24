# UAQF Backend

Live FastAPI forecast API for the Urban Air Quality Forecasting app. The Pydantic
schemas in [`app/schemas.py`](app/schemas.py) are the **OpenAPI contract** — the
frontend's TypeScript types are generated from it, never hand-synced.

> Phase 0 serves clearly-labeled **seed** data (`data_source: "seed"`, `model_version:
> "seed-*"`, `beats_baseline: false`) so the full contract is exercisable before the
> real ETL (Phase 1) and model (Phase 3) land. No value is ever presented as a real,
> validated measurement until those phases replace the seed provider.

## Run (uv)

```bash
uv sync                              # creates .venv on Python 3.12, installs deps
uv run uvicorn app.main:app --reload # http://127.0.0.1:8000  (docs at /docs)
```

## Checks

```bash
uv run ruff check .
uv run mypy app
uv run pytest
uv run python scripts/export_openapi.py   # regenerate ../openapi.json (the contract)
```

## Contract endpoints

| Method | Path         | Purpose                                              |
|--------|--------------|------------------------------------------------------|
| GET    | `/health`    | liveness + data freshness + upstream status          |
| GET    | `/stations`  | monitoring stations + latest readings                |
| GET    | `/forecast`  | per-station, per-pollutant forecast (`?station_id&pollutant&horizon`) |

Every forecast surface carries `data_as_of` + `stale` (HL1), a persistence `baseline`
and `beats_baseline` (HL2), per-point `interpolated` flags (HL3), and a `disclaimer`
(HL4). See [`../rules.md`](../rules.md) for the full hard-limit list.
