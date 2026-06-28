"""ML inference engine for forecasting.

Loads the committed per-pollutant, per-horizon residual models and the registry, and turns
the latest stored feature row into a forecast. Two honesty rules are enforced here so the
serving layer can never drift from the evidence:

* The model predicts a *residual* (change from the current value); the level is reconstructed
  as ``current + Δ̂`` and floored at zero — the same reconstruction used during evaluation.
* ``beats_baseline`` and ``model_version`` are read straight from ``registry.json`` (the
  committed walk-forward evaluation). The engine never asserts a model beats the baseline
  on its own — if the registry says it does not, the API will say so too (HL2).
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import joblib
import pandas as pd
from app.ingestion.storage import default_data_dir
from app.modeling.cv import feature_columns
from app.modeling.train import MODEL_VERSION
from app.schemas import Pollutant

logger = logging.getLogger("uaqf.modeling.inference")


class InferenceEngine:
    """Loads trained models and executes forecasting logic."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or default_data_dir()
        self.models_dir = self.data_dir.parent / "models"
        self.features_path = self.data_dir / "features" / "features.parquet"
        self.registry_path = self.models_dir / "registry.json"

        # Per pollutant: a {horizon: estimator} dict (direct multi-step models).
        self.models: dict[str, dict[int, Any]] = {}
        self.registry: dict[str, Any] = {}
        self._load_registry()
        self._load_models()

    def _load_registry(self) -> None:
        if self.registry_path.exists():
            try:
                self.registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("failed_to_load_registry", extra={"error": str(e)})

    def _load_models(self) -> None:
        for pol in Pollutant:
            model_file = self.models_dir / f"{pol.value}_model.joblib"
            if model_file.exists():
                try:
                    loaded = joblib.load(model_file)
                    # Stored as {horizon: estimator}; keys may deserialize as str.
                    self.models[pol.value] = {int(h): est for h, est in loaded.items()}
                except Exception as e:
                    logger.warning(
                        "failed_to_load_model", extra={"pollutant": pol.value, "error": str(e)}
                    )

    def has_model(self, pollutant: Pollutant) -> bool:
        return bool(self.models.get(pollutant.value))

    def beats_baseline(self, pollutant: Pollutant) -> bool:
        """Read the committed verdict — never recomputed or assumed (HL2)."""
        return bool(self.registry.get(pollutant.value, {}).get("beats_baseline", False))

    def model_version(self, pollutant: Pollutant) -> str:
        return str(self.registry.get(pollutant.value, {}).get("model_version", MODEL_VERSION))

    def _historical_rmse(self, pollutant: str, horizon: int) -> float:
        """Per-horizon holdout RMSE from the registry; falls back to a wide band."""
        try:
            val = self.registry[pollutant]["metrics"]["rmse"].get(str(horizon))
            if val is not None:
                return float(val)
        except Exception:
            pass
        return 5.0

    def _latest_feature_row(self, station_id: str) -> pd.Series:
        if not self.features_path.exists():
            raise FileNotFoundError("Features parquet not found.")
        con = duckdb.connect()
        try:
            df = con.execute(
                f"SELECT * FROM read_parquet('{self.features_path.as_posix()}') "
                "WHERE station_id = ? ORDER BY ts DESC LIMIT 1",
                [station_id],
            ).df()
        finally:
            con.close()
        if len(df) == 0:
            raise ValueError(f"No features found for station {station_id}")
        return df.iloc[0]

    def predict(
        self, station_id: str, pollutant: Pollutant, horizon_hours: int
    ) -> list[tuple[datetime, float, float, float]]:
        """Forecast horizons 1..horizon_hours.

        Returns ``(target_ts, value, lower, upper)`` tuples. The value is the residual model's
        ``current + Δ̂`` reconstruction, floored at zero; the band is +/-1.96 x the per-horizon
        holdout RMSE.
        """
        models = self.models.get(pollutant.value)
        if not models:
            raise ValueError(f"No trained model for {pollutant.value}")

        latest = self._latest_feature_row(station_id)
        base_ts = latest["ts"]
        if base_ts.tzinfo is None:
            base_ts = base_ts.replace(tzinfo=UTC)
        current = float(latest[pollutant.value])

        feat_cols = feature_columns(pollutant.value)
        results: list[tuple[datetime, float, float, float]] = []
        for h in range(1, horizon_hours + 1):
            model = models.get(h)
            if model is None:
                raise ValueError(f"No model for {pollutant.value} horizon {h}")
            row = latest.to_dict()
            row["horizon"] = h
            frame = pd.DataFrame([row])
            delta = float(model.predict(frame[feat_cols])[0])
            value = max(0.0, current + delta)

            rmse = self._historical_rmse(pollutant.value, h)
            lower = max(0.0, value - 1.96 * rmse)
            upper = value + 1.96 * rmse
            results.append((base_ts + pd.Timedelta(hours=h), value, lower, upper))

        return results


# Singleton engine (lazy loaded)
_engine: InferenceEngine | None = None


def get_inference_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine
