#!/usr/bin/env python
"""Train + certify the forecasting models on whatever is in the feature store.

This is the **live-data** entry point. It shares its entire evaluation and certification
path with the synthetic reproducer (`scripts/seed_and_train.py`) via
`app.modeling.train.build_registry`, so there is exactly one honest definition of
"beats the baseline" — no second, divergent training routine that could quietly disagree
with the committed metrics. Run it after an ingest window has accumulated enough history:

  uv run python -m scripts.train_model
"""

import os

# Single-threaded for reproducible gradient-boosted histograms (see seed_and_train).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import json
import logging
import sys

import joblib
import pandas as pd
from app.config import get_settings
from app.ingestion.storage import default_data_dir
from app.logging_config import configure_logging
from app.modeling.train import HORIZONS, build_registry

logger = logging.getLogger("uaqf.scripts.train_model")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    data_dir = default_data_dir()
    features_path = data_dir / "features" / "features.parquet"
    models_dir = data_dir.parent / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    if not features_path.exists():
        logger.error("Features file not found. Run scripts/run_features.py first.")
        sys.exit(1)

    df = pd.read_parquet(features_path)
    registry, models = build_registry(df, HORIZONS)
    if not registry:
        logger.error("No pollutant accumulated enough data to evaluate.")
        sys.exit(1)

    for pol, model in models.items():
        joblib.dump(model, models_dir / f"{pol}_model.joblib")
    (models_dir / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")

    for pol, entry in registry.items():
        logger.info(
            "model_certified",
            extra={"pollutant": pol, "beats_baseline": entry["beats_baseline"]},
        )
    logger.info("modeling_completed", extra={"registry": str(models_dir / "registry.json")})


if __name__ == "__main__":
    main()
