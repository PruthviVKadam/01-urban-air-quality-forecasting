# Model Card: Atmosphere HistGradientBoostingRegressor

This document details the machine learning models used in the Atmosphere Air Quality Forecasting app.

## Model Details
- **Architecture**: `HistGradientBoostingRegressor` (scikit-learn).
- **Type**: Global / Direct Multi-Step Horizon forecasting.
- **Pollutants**: PM₂.₅, O₃, NO₂ (separate model per pollutant).
- **Features**: Cyclical time components (sin/cos hour & day of week), 1h & 24h lags, 24h rolling means, weather parameters (temperature, humidity, wind speed, pressure), and integer forecast horizon.
- **Objective Function**: Squared Error (RMSE).

## Intended Use
- **Primary Use**: Forecasting hourly pollutant concentrations 1 to 24 hours into the future for specific monitoring stations.
- **Out of Scope**: Not to be used as medical or health advice. Not intended for multi-day forecasting (>24h).

## Training Data
- **Source**: OpenAQ (pollutants) + Open-Meteo (weather).
- **Data Window**: Dynamically evaluated on the available `features.parquet` store.
- **Exclusions**: Data failing bounds checks (e.g., negative concentrations) are filtered at the ETL layer.

## Performance & Baselines (G2 Gate)

> [!WARNING]
> Due to insufficient historical data at the time of implementation (Phase 3 launch), the model has not yet accumulated enough training samples to establish definitive baseline-beating metrics. This model card will be automatically updated by `scripts/train_model.py` and `registry.json` once sufficient data is gathered.

Target Exceedance Thresholds used for Precision/Recall:
- **PM₂.₅**: 35.5 µg/m³ (Unhealthy for Sensitive Groups)
- **O₃**: 70.0 ppb
- **NO₂**: 100.0 ppb

*Expected metrics will be updated here once `train_model.py` completes a successful run.*

## Known Failure Modes
- **Rapid Weather Fronts**: The model heavily relies on lag features. If a sudden weather shift blows in pollution without precedent in the recent 24-hour window, the model may underpredict the initial spike.
- **Sensor Outages**: If a station goes offline, the ETL layer falls back to interpolating. If a station is offline for >3 hours, the model predictions will degrade and the UI will flag them as stale.
- **Holiday/Event Anomalies**: Fireworks (e.g., July 4th) or localized fires can cause massive PM₂.₅ spikes that the model cannot foresee based solely on weather and historical lags.

## Refresh Cadence
- **Recommendation**: Models should be retrained via `scripts/train_model.py` weekly to adapt to seasonal shifts and newly added stations.
