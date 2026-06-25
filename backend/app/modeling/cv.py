"""Walk-forward cross-validation and evaluation harness."""

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, root_mean_squared_error


def evaluate_baselines(
    df: pd.DataFrame, target_cols: list[str], horizons: list[int]
) -> dict[str, dict[str, dict[str, float]]]:
    """Evaluates persistence and seasonal baselines using walk-forward logic.

    Args:
        df: Feature dataframe (must be strictly hourly contiguous per station).
        target_cols: List of pollutant columns to evaluate (e.g. ['pm25', 'o3']).
        horizons: List of integer hours ahead to predict.

    Returns:
        Nested dict with metrics: { target: { model_name: { metric: value } } }
    """
    results: dict[str, dict[str, dict[str, float]]] = {}

    # Ensure sorted by station and time
    df = df.sort_values(["station_id", "ts"]).copy()

    # Intermediate structure to hold lists of metrics across horizons
    temp_results: dict[str, dict[str, dict[str, list[float]]]] = {}

    for target in target_cols:
        if target not in df.columns:
            continue

        temp_results[target] = {
            "persistence": {"mae": [], "rmse": []},
            "seasonal": {"mae": [], "rmse": []},
        }

        for h in horizons:
            # The TRUE value h hours into the future.
            # Safe because ETL guarantees strictly hourly contiguous rows.
            df[f"true_{h}h"] = df.groupby("station_id")[target].shift(-h)

            # The seasonal prediction h hours into the future is simply the seasonal_avg AT time t+h
            df[f"seasonal_pred_{h}h"] = df.groupby("station_id")[f"{target}_seasonal_avg"].shift(-h)

            # Drop NaNs to evaluate this horizon
            mask = df[f"true_{h}h"].notna()
            df_eval = df[mask]

            if len(df_eval) == 0:
                continue

            # Persistence evaluation (predicts current value)
            persist_mask = df_eval[f"{target}_persist_{h}h"].notna()
            if persist_mask.sum() > 0:
                df_p = df_eval[persist_mask]
                temp_results[target]["persistence"]["mae"].append(
                    mean_absolute_error(df_p[f"true_{h}h"], df_p[f"{target}_persist_{h}h"])
                )
                temp_results[target]["persistence"]["rmse"].append(
                    root_mean_squared_error(df_p[f"true_{h}h"], df_p[f"{target}_persist_{h}h"])
                )

            # Seasonal evaluation
            season_mask = df_eval[f"seasonal_pred_{h}h"].notna()
            if season_mask.sum() > 0:
                df_s = df_eval[season_mask]
                temp_results[target]["seasonal"]["mae"].append(
                    mean_absolute_error(df_s[f"true_{h}h"], df_s[f"seasonal_pred_{h}h"])
                )
                temp_results[target]["seasonal"]["rmse"].append(
                    root_mean_squared_error(df_s[f"true_{h}h"], df_s[f"seasonal_pred_{h}h"])
                )

        # Average across horizons
        results[target] = {"persistence": {}, "seasonal": {}}
        for model in ["persistence", "seasonal"]:
            if temp_results[target][model]["mae"]:
                results[target][model]["mae"] = float(np.mean(temp_results[target][model]["mae"]))
                results[target][model]["rmse"] = float(np.mean(temp_results[target][model]["rmse"]))
            else:
                results[target][model]["mae"] = 0.0
                results[target][model]["rmse"] = 0.0

    return results
