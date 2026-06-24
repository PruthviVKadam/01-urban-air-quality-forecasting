# rules.md — Urban Air Quality Forecasting

**These are hard limits and gates, not guidance.** If a change violates a Hard Limit, do not ship it. If a Gate is red, do not advance to the next phase. These rules are specific to this project; do not import rules from the other folders.

---

## Hard Limits (HL) — never violate

- **HL1 — Freshness is mandatory.** No pollutant value or forecast may render anywhere in the UI or API without an attached `data_as_of` timestamp. Data older than **3 hours** must be visually flagged as stale in the UI and carry `"stale": true` in the payload.
- **HL2 — No model without a baseline shadow.** Every forecast response includes the persistence-baseline value and a `beats_baseline` boolean. The UI shows the baseline line on every forecast chart. A model that does not beat persistence on the validation window is not allowed in production (see Gate G2).
- **HL3 — No silent imputation.** Interpolated or backfilled readings must carry an `interpolated: true` flag from ETL → API → UI, and be visually distinct (e.g. dashed/hollow) in every chart. Gaps longer than the documented max are shown as gaps, not filled.
- **HL4 — Not medical advice.** The app may display the official AQI category and EPA descriptor text only. It must **not** generate personalized health, medication, or exposure advice. A persistent disclaimer ("Informational forecast — not medical guidance") is required on any alert surface.
- **HL5 — Latency & resilience budget.** A `/forecast` request returns in **< 800 ms p95** from cache and **must never block** on a live upstream fetch. Any external API call uses timeout (≤ 5 s), retry with backoff + jitter (max 3), and a circuit breaker. Upstream failure → serve last-known-good + `stale` flag, never a 500 to the user.
- **HL6 — Secrets discipline.** No API keys, tokens, or credentials in source or git history. Everything via env vars with a committed `.env.example`. The project must run on documented free tiers.
- **HL7 — Time-series integrity.** No random-split cross-validation, ever. No feature may use information from the future of its target (no leakage). Walk-forward CV only.

## Gating Checkpoints (G) — must be green to advance

- **G0 — Contract & CI.** OpenAPI schema committed; TS types generated from it; lint + type-check + test jobs run in CI on every push. *Blocks Phase 1.*
- **G1 — Data Quality.** ETL passes schema/range/gap/duplicate validation on a 30-day pull for ≥ 3 stations; quarantine path proven with an injected bad batch; interpolation flags verified end to end. *Blocks Phase 2.*
- **G2 — Model beats baseline.** Chosen model beats both persistence and seasonal-average baselines on MAE **and** RMSE for every (pollutant × horizon) pair on the walk-forward holdout. Exceedance-event recall ≥ documented target. Model card committed. *Blocks promotion to the serving layer.*
- **G3 — API reliability.** Integration tests against recorded fixtures pass; chaos test (kill upstream) confirms graceful degradation; load smoke test meets HL5 latency. *Blocks Phase 5.*
- **G4 — Accessibility & color.** AQI palette is verified color-blind-safe (do **not** rely on red/green alone — pair color with shape/label/value). Full keyboard navigation; visible focus states; `prefers-reduced-motion` respected; map has a non-map fallback table. *Blocks release.*
- **G5 — Release readiness.** All HLs satisfied, G0–G4 green, e2e tests pass, deployed URL smoke-tested, README complete with data-source licenses. *Blocks "done".*

---

## Reliability & Robustness Mandates

This project lives or dies on robustness — it consumes flaky public sensor feeds. Build defensively from line one.

- **Fail loud in dev, soft in prod.** Validation errors raise in tests/CI; in production they degrade to last-known-good with a user-visible notice and a logged alert.
- **Every external dependency is assumed unreliable.** Wrap OpenAQ, AirNow, and weather calls behind a client with timeout + retry + circuit breaker + cache. A single offline sensor must never blank the map — render the rest, mark the gap.
- **Idempotent, replayable ETL.** Re-running ingestion for a window produces the same processed output. Raw pulls in `data/raw/` are immutable; all cleaning is downstream and reproducible.
- **Determinism.** Seed all RNGs (numpy, torch). Pin dependency versions. Record the training data window in the model registry so any forecast is reproducible.
- **Explicit states in the UI.** Every data-bound component implements four states: loading (skeleton), empty, error (with retry), and stale. No infinite spinners; no blank panels.
- **Observability.** Structured logs with request ids; `/health` exposes last-refresh time, upstream status, and cache hit rate. Errors are categorized (upstream vs internal vs validation).
- **Testing floor.** Unit tests for every transform and the exceedance classifier; integration tests against recorded API fixtures (no live network in CI); at least one Playwright e2e covering map-click → horizon-scrub → pollutant-toggle.
- **Reduced-motion & low-end devices.** All motion must have a `prefers-reduced-motion` path; the map must stay interactive on a mid-range laptop (no jank when scrubbing the horizon).

## Design Guardrails (enforced; full spec in DESIGN.md)

- Playful and bold is required — **generic "AI-generated dashboard" look is forbidden** (no default-template purple gradient hero, no emoji-as-iconography, no untouched component-library defaults). See `DESIGN.md` → Anti-Slop Checklist.
- Interactivity is a hard requirement, not a nice-to-have: any panel that cannot respond to user input must be redesigned or cut.
- Data honesty beats visual drama: never style away uncertainty. Confidence bands, stale flags, and interpolation markers must remain legible.

## Definition of Done (this project)

A stranger can open the deployed URL, click a station on a bold living map, drag the forecast 24 hours into the future and watch the city recolor, switch pollutants with a satisfying transition — and at every moment they can see how fresh the data is, how confident the model is, and that it beats the naive baseline. It never crashes when a sensor goes dark.
