"""Model training + registry construction (shared by live and synthetic pipelines).

This is the single place that decides — honestly — whether a model earns the
``beats_baseline`` flag. It runs the walk-forward evaluation (model vs persistence vs
seasonal, per pollutant x horizon), fits the final per-pollutant models on all data, and
assembles the registry that the serving layer reads. The serving layer never re-derives
``beats_baseline``; it only reports what this committed evaluation found (HL2).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import pandas as pd
from app.modeling.cv import feature_columns, fit_horizon_models, walk_forward_evaluate
from app.modeling.metrics import EXCEEDANCE_THRESHOLDS

logger = logging.getLogger("uaqf.modeling.train")

MODEL_VERSION = "hist-gbdt-1.0"
TARGET_POLLUTANTS = ["pm25", "o3", "no2"]
HORIZONS = list(range(1, 25))


def fit_final_models(df: pd.DataFrame, target_col: str, horizons: list[int]) -> dict[int, Any]:
    """Fit the production per-horizon residual models for one pollutant on all history."""
    return fit_horizon_models(df.sort_values(["station_id", "ts"]), target_col, horizons)


def build_registry_entry(df: pd.DataFrame, target_col: str, horizons: list[int]) -> dict[str, Any]:
    """Evaluate, fit, and assemble the registry entry for one pollutant."""
    report = walk_forward_evaluate(df, target_col, horizons)

    # Reshape per-horizon model metrics into the {metric: {horizon: value}} layout the
    # inference engine expects (it reads metrics.rmse[h] for the confidence band).
    mae = {h: report["per_horizon"][h]["model"]["mae"] for h in report["per_horizon"]}
    rmse = {h: report["per_horizon"][h]["model"]["rmse"] for h in report["per_horizon"]}
    recall = {
        h: report["per_horizon"][h]["model"]["exceedance_recall"] for h in report["per_horizon"]
    }

    window = {
        "start": str(pd.Timestamp(df["ts"].min())),
        "end": str(pd.Timestamp(df["ts"].max())),
        "n_rows": len(df),
        "n_stations": int(df["station_id"].nunique()),
    }

    return {
        "model_path": f"{target_col}_model.joblib",
        "model_version": MODEL_VERSION,
        "beats_baseline": bool(report["beats_baseline"]),
        "horizons_scored": report["horizons_scored"],
        "horizons_beaten": report["horizons_beaten"],
        "exceedance_threshold": EXCEEDANCE_THRESHOLDS.get(target_col),
        "training_params": {"features": feature_columns(target_col), "train_window": window},
        "metrics": {"mae": mae, "rmse": rmse, "exceedance_recall": recall},
        "baselines": {
            "persistence": report["summary"]["persistence"],
            "seasonal": report["summary"]["seasonal"],
        },
        "summary": report["summary"],
    }


def build_registry(
    df: pd.DataFrame, horizons: list[int] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the full registry and fit final models for every pollutant with data.

    Returns ``(registry, models)`` where ``models`` maps pollutant -> fitted estimator.
    """
    horizons = horizons or HORIZONS
    registry: dict[str, Any] = {}
    models: dict[str, Any] = {}

    for target in TARGET_POLLUTANTS:
        if target not in df.columns or df[target].notna().sum() < 100:
            logger.warning("skip_pollutant_insufficient_data", extra={"pollutant": target})
            continue
        logger.info("evaluating_pollutant", extra={"pollutant": target})
        entry = build_registry_entry(df, target, horizons)
        models[target] = fit_final_models(df, target, horizons)
        registry[target] = entry
        logger.info(
            "pollutant_done",
            extra={
                "pollutant": target,
                "beats_baseline": entry["beats_baseline"],
                "horizons_beaten": f"{entry['horizons_beaten']}/{entry['horizons_scored']}",
            },
        )

    return registry, models


def generated_at() -> str:
    """UTC timestamp string for stamping the model card / registry metadata."""
    return datetime.now().astimezone().isoformat(timespec="seconds")
