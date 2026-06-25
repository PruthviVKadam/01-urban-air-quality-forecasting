#!/usr/bin/env python
"""Train Gradient Boosted Trees for air quality forecasting."""

import json
import logging
import sys

import joblib
import pandas as pd
from app.config import get_settings
from app.ingestion.storage import default_data_dir
from app.logging_config import configure_logging
from app.modeling.metrics import calculate_exceedance_metrics
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error

logger = logging.getLogger("uaqf.scripts.train_model")


def prepare_training_data(df: pd.DataFrame, target_col: str, horizons: list[int]) -> pd.DataFrame:
    """Expands the dataset by duplicating it for each horizon.
    The target becomes the future value at t+h.
    """
    chunks = []

    for h in horizons:
        df_h = df.copy()
        df_h["horizon"] = h
        # Future value we want to predict
        df_h["future_target"] = df_h.groupby("station_id")[target_col].shift(-h)
        # Drop rows where we don't have the future target
        df_h = df_h.dropna(subset=["future_target"])
        chunks.append(df_h)

    return pd.concat(chunks, ignore_index=True)


def train_and_evaluate(
    df: pd.DataFrame, target_col: str
) -> tuple[HistGradientBoostingRegressor, dict, dict]:
    """Trains a model and evaluates it on a time-based holdout (last 20% of time)."""
    horizons = list(range(1, 25))

    # 1. Prepare data
    feature_cols = [
        "sin_hour",
        "cos_hour",
        "sin_dow",
        "cos_dow",
        f"{target_col}_lag_1h",
        f"{target_col}_lag_24h",
        f"{target_col}_roll_mean_24h",
        "temperature_c",
        "humidity_pct",
        "wind_speed_ms",
        "pressure_hpa",
        "horizon",
    ]

    # We must ensure no leakage. We split the ORIGINAL dataframe by time first.
    # Because if we expand first, the future target of the training set might leak into the test set's time!
    # Wait, if we split at time T, training set uses X up to T. Its targets go up to T+24.
    # Test set uses X from T+1. Its targets go up to T+1+24.
    # This is safe because training never sees X from T+1.

    unique_times = df["ts"].sort_values().unique()
    if len(unique_times) < 10:
        logger.warning(
            "Not enough data to train properly. Will train anyway for pipeline verification."
        )
        split_idx = int(len(unique_times) * 0.5)
    else:
        split_idx = int(len(unique_times) * 0.8)

    split_time = unique_times[split_idx]

    df_train_orig = df[df["ts"] <= split_time].copy()
    df_test_orig = df[df["ts"] > split_time].copy()

    if len(df_train_orig) == 0 or len(df_test_orig) == 0:
        logger.error(f"Cannot split data for {target_col}. Not enough timestamps.")
        return HistGradientBoostingRegressor(), {}, {}

    df_train = prepare_training_data(df_train_orig, target_col, horizons)
    df_test = prepare_training_data(df_test_orig, target_col, horizons)

    # Fill weather NaNs if any, though HistGradientBoostingRegressor handles NaNs!
    # Just need to make sure the target is not NaN (already dropped)

    X_train = df_train[feature_cols]
    y_train = df_train["future_target"]

    X_test = df_test[feature_cols]
    df_test["future_target"]

    if len(X_train) < 20:
        logger.warning(
            f"Training set for {target_col} is very small ({len(X_train)} rows). Skipping training."
        )
        return HistGradientBoostingRegressor(), {}, {}

    use_early_stopping = len(X_train) >= 50

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        max_iter=100,
        learning_rate=0.1,
        early_stopping=use_early_stopping,
        random_state=42,
    )

    model.fit(X_train, y_train)

    # 3. Evaluate on Holdout
    metrics = {"mae": {}, "rmse": {}, "exceedance_recall": {}}

    if len(X_test) > 0:
        y_pred = model.predict(X_test)
        df_test["pred"] = y_pred

        for h in horizons:
            mask = df_test["horizon"] == h
            if mask.sum() == 0:
                continue

            y_t = df_test[mask]["future_target"]
            y_p = df_test[mask]["pred"]

            mae = mean_absolute_error(y_t, y_p)
            rmse = root_mean_squared_error(y_t, y_p)
            exc = calculate_exceedance_metrics(y_t, y_p, target_col)

            metrics["mae"][str(h)] = float(mae)
            metrics["rmse"][str(h)] = float(rmse)
            metrics["exceedance_recall"][str(h)] = exc["recall"]

    # Train final model on ALL data
    df_all = prepare_training_data(df, target_col, horizons)
    X_all = df_all[feature_cols]
    y_all = df_all["future_target"]

    final_model = HistGradientBoostingRegressor(
        loss="squared_error", max_iter=100, learning_rate=0.1, random_state=42
    )
    if len(X_all) > 0:
        final_model.fit(X_all, y_all)

    return final_model, metrics, {"features": feature_cols, "split_time": str(split_time)}


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    data_dir = default_data_dir()
    features_path = data_dir / "features" / "features.parquet"
    models_dir = data_dir.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if not features_path.exists():
        logger.error("Features file not found.")
        sys.exit(1)

    df = pd.read_parquet(features_path)
    target_cols = ["pm25", "o3", "no2"]

    registry = {}

    for target in target_cols:
        if target not in df.columns:
            continue

        logger.info(f"Training model for {target.upper()}...")
        model, metrics, params = train_and_evaluate(df, target)

        if not metrics:
            logger.warning(f"Skipping {target} due to insufficient data.")
            continue

        # Save model
        model_path = models_dir / f"{target}_model.joblib"
        joblib.dump(model, model_path)

        # Calculate averages for the registry summary
        avg_mae = sum(metrics["mae"].values()) / len(metrics["mae"]) if metrics["mae"] else 0.0
        avg_rmse = sum(metrics["rmse"].values()) / len(metrics["rmse"]) if metrics["rmse"] else 0.0

        registry[target] = {
            "model_path": str(model_path.name),
            "hyperparameters": model.get_params(),
            "training_params": params,
            "metrics": metrics,
            "summary": {"avg_mae": avg_mae, "avg_rmse": avg_rmse},
        }

    # Save registry
    registry_path = models_dir / "registry.json"
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    logger.info("modeling_completed", extra={"registry": str(registry_path)})


if __name__ == "__main__":
    main()
