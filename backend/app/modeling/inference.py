"""ML inference engine for forecasting."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, List, Tuple

import duckdb
import joblib
import pandas as pd

from app.ingestion.storage import default_data_dir
from app.schemas import Pollutant

logger = logging.getLogger("uaqf.modeling.inference")

class InferenceEngine:
    """Loads trained models and executes forecasting logic."""
    
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or default_data_dir()
        self.models_dir = self.data_dir.parent / "models"
        self.features_path = self.data_dir / "features" / "features.parquet"
        self.registry_path = self.models_dir / "registry.json"
        
        self.models = {}
        self.registry = {}
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
                    self.models[pol.value] = joblib.load(model_file)
                except Exception as e:
                    logger.warning("failed_to_load_model", extra={"pollutant": pol.value, "error": str(e)})
                    
    def _get_historical_rmse(self, pollutant: str, horizon: int) -> float:
        """Fallback to 5.0 if not found."""
        try:
            val = self.registry.get(pollutant, {}).get("metrics", {}).get("rmse", {}).get(str(horizon))
            if val is not None:
                return float(val)
        except Exception:
            pass
        return 5.0

    def predict(self, station_id: str, pollutant: Pollutant, horizon_hours: int) -> List[Tuple[datetime, float, float, float]]:
        """
        Runs ML prediction for horizons 1..horizon_hours.
        Returns: list of (target_ts, predicted_value, lower_bound, upper_bound)
        """
        if pollutant.value not in self.models:
            raise ValueError(f"No trained model for {pollutant.value}")
            
        if not self.features_path.exists():
            raise FileNotFoundError("Features parquet not found.")
            
        # 1. Fetch the LATEST feature row for the station
        con = duckdb.connect()
        try:
            # We want the single most recent row for the station
            query = f"""
                SELECT * FROM read_parquet('{self.features_path.as_posix()}')
                WHERE station_id = '{station_id}'
                ORDER BY ts DESC
                LIMIT 1
            """
            df_latest = con.execute(query).df()
        finally:
            con.close()
            
        if len(df_latest) == 0:
            raise ValueError(f"No features found for station {station_id}")
            
        latest_row = df_latest.iloc[0]
        base_ts = latest_row['ts']
        
        # Ensure base_ts has timezone info
        if base_ts.tzinfo is None:
            base_ts = base_ts.replace(tzinfo=UTC)
            
        # 2. Extract features exactly as trained
        try:
            feature_cols = self.registry[pollutant.value]["training_params"]["features"]
        except KeyError:
            # Fallback if registry is missing or malformed
            feature_cols = [
                'sin_hour', 'cos_hour', 'sin_dow', 'cos_dow',
                f'{pollutant.value}_lag_1h', f'{pollutant.value}_lag_24h', f'{pollutant.value}_roll_mean_24h',
                'temperature_c', 'humidity_pct', 'wind_speed_ms', 'pressure_hpa',
                'horizon'
            ]
            
        # 3. Create prediction batch for h=1..horizon_hours
        batch_rows = []
        target_timestamps = []
        
        for h in range(1, horizon_hours + 1):
            row_dict = latest_row.to_dict()
            row_dict['horizon'] = h
            batch_rows.append(row_dict)
            target_timestamps.append(base_ts + pd.Timedelta(hours=h))
            
        df_batch = pd.DataFrame(batch_rows)
        
        # Verify no NaN in essential features except maybe weather which HistGradientBoosting can handle
        # But if the pollutant lag is NaN, we might have an issue. 
        # HistGradientBoostingRegressor natively supports NaNs!
        X = df_batch[feature_cols]
        
        # 4. Predict
        model = self.models[pollutant.value]
        preds = model.predict(X)
        
        # 5. Format results
        results = []
        for i, h in enumerate(range(1, horizon_hours + 1)):
            pred_val = float(preds[i])
            # Ensure no negative predictions (Poisson/Squared error might dip < 0)
            pred_val = max(0.0, pred_val)
            
            rmse = self._get_historical_rmse(pollutant.value, h)
            # 95% CI ~ +/- 1.96 * RMSE
            lower = max(0.0, pred_val - (1.96 * rmse))
            upper = pred_val + (1.96 * rmse)
            
            results.append((target_timestamps[i], pred_val, lower, upper))
            
        return results

# Singleton engine (lazy loaded)
_engine = None

def get_inference_engine() -> InferenceEngine:
    global _engine
    if _engine is None:
        _engine = InferenceEngine()
    return _engine
