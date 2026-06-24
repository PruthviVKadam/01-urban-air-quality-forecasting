# data-sources.md — Urban Air Quality Forecasting

Every source below must be wrapped in the resilient client described in `rules.md` (timeout + retry + circuit breaker + cache). Rate limits and auth schemes change — **verify the current values in each provider's docs before relying on them**, and encode the real limit as a config constant.

## Pollutant data

### OpenAQ — primary pollutant feed
- **What:** Global open air-quality measurements (PM₂.₅, PM₁₀, O₃, NO₂, SO₂, CO).
- **Access:** REST API (current major version v3). Requires a **free API key** (header auth).
- **License:** Open data (CC BY 4.0 for most providers) — attribute OpenAQ and underlying sources.
- **Failure behavior:** On 429/5xx → back off, serve last-known-good, set `stale`. Never block a user request on a live OpenAQ call.
- **Docs:** https://docs.openaq.org/

### EPA AirNow — US authoritative AQI
- **What:** Official US AQI + reporting-area data; good for the EPA category/descriptor text used in the UI.
- **Access:** Free API key required. **Rate limit is strict (historically ~500 requests/hour)** — confirm and respect it; cache aggressively and batch by reporting area.
- **License:** US Government data; follow AirNow data-use guidelines and attribution.
- **Failure behavior:** Treat as enrichment, not a hard dependency — the app must still forecast if AirNow is down.
- **Docs:** https://docs.airnowapi.org/

## Weather data (exogenous features)

### Open-Meteo — recommended weather source
- **What:** Temperature, humidity, wind, pressure — historical + forecast.
- **Access:** **Free, no API key** for non-commercial use; generous limits.
- **License:** CC BY 4.0.
- **Why preferred:** No-key simplicity keeps the repo runnable for reviewers.
- **Docs:** https://open-meteo.com/

### NOAA (NWS / integrated surface data) — alternative/validation
- **What:** US weather observations and forecasts.
- **Access:** Free; some endpoints keyed. Heavier to integrate than Open-Meteo.
- **Docs:** https://www.weather.gov/documentation/services-web-api

## Optional augmentation
- City open-data portals for traffic/industrial proxies (varies by city; treat as fully optional and behind a feature flag).

---

## Integration rules (recap from rules.md)

- Store raw pulls immutably in `data/raw/`; cleaned series in `data/processed/`.
- Tag every interpolated reading (`interpolated: true`) end to end.
- Each provider gets a config block: base URL, key env var, timeout, retry policy, documented rate limit, cache TTL.
- Attribution for OpenAQ, AirNow, and Open-Meteo must appear in the app footer and the README.
- No keys in source — `.env` only; commit `.env.example` with placeholder names.
