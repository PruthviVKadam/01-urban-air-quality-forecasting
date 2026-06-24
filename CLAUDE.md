# CLAUDE.md — Urban Air Quality Forecasting

> This file is loaded automatically by Claude Code. Treat it as standing orders for every session in this folder. **Read `rules.md` in full before writing any code.** The rules there are hard limits, not suggestions.

## What this project is

A real-time **Urban Air Quality Forecasting** web app. It pulls live pollutant readings (PM₂.₅, O₃, NO₂) and weather, forecasts the next 6–24 hours per monitoring station, and presents it as an **interactive city map explorer** that a non-expert genuinely wants to click around in. This is a portfolio *product*, not a notebook dump.

## The three things that matter, in order

1. **Reliability first.** The app must never crash on a missing sensor, a rate-limited API, or a stale feed. It degrades gracefully and *tells the user what it's showing and how fresh it is*. A forecast with no visible "data as of" timestamp is a bug. See `rules.md` → Hard Limits.
2. **Interactive, not a showcase.** Every screen has controls that change what the user sees: click a station on the map, scrub the forecast horizon, toggle pollutants, animate the timeline. If a panel only displays and never responds, redesign it. See `DESIGN.md` → Interactivity Spec.
3. **Intriguing by design.** Playful, bold, atmosphere-themed — and deliberately *not* generic AI-generated-looking. The anti-slop rules in `DESIGN.md` are mandatory.

## Architecture (locked)

- **Frontend:** React + Vite + TypeScript + Tailwind. Map via MapLibre GL (open, no token). Charts via **visx** or **Recharts** (custom-styled — see DESIGN). Motion via Framer Motion.
- **Backend:** **FastAPI** (Python) serving forecasts and station metadata over a typed REST API. This is the "live backend API" — the frontend never embeds model code.
- **ML:** Python time-series stack (pandas, statsmodels, scikit-learn, XGBoost/LightGBM, PyTorch for LSTM/GRU). Models are trained offline; the API serves cached forecasts and refreshes them on a schedule.
- **Contract:** Frontend and backend agree on an OpenAPI schema. Generate TS types from it; never hand-sync shapes.

## Where to read before doing

| Need | File |
|------|------|
| Build order, phases, milestones | `plan.md` |
| Hard limits, gating, robustness mandates | `rules.md` |
| Visual system, motion, anti-AI-slop, interactivity | `DESIGN.md` |
| APIs, licenses, rate limits, failure behavior | `data-sources.md` |

## Definition of done (every PR/phase)

- Tests pass (unit + at least one integration test against a recorded API fixture).
- No forecast renders without a freshness timestamp and a model-vs-baseline indicator.
- AQI colors are color-blind-safe (see `rules.md` → Gating G4).
- The new surface is *interactive* — it responds to user input — and matches the `DESIGN.md` motion budget.
- `rules.md` gates relevant to the change are green.

## Hard "do nots" (full list in rules.md)

- Do **not** present any health/exposure guidance as medical advice. Show the AQI category and the official EPA descriptor only.
- Do **not** ship a model that loses to the persistence baseline. Gate G2 blocks it.
- Do **not** silently interpolate missing sensor data — interpolated points must be flagged in the API payload and the UI.
- Do **not** hardcode API keys. Use env vars; the repo must run with documented free-tier keys.
