#!/usr/bin/env python
"""Evaluates persistence and seasonal baselines on the feature dataset."""

import json
import logging
import sys

import pandas as pd
from app.config import get_settings
from app.ingestion.storage import default_data_dir
from app.logging_config import configure_logging
from app.modeling.baselines import add_persistence_baseline, add_seasonal_baseline
from app.modeling.cv import evaluate_baselines

logger = logging.getLogger("uaqf.scripts.evaluate_baselines")

def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    
    data_dir = default_data_dir()
    features_path = data_dir / "features" / "features.parquet"
    
    if not features_path.exists():
        logger.error("Features file not found. Run scripts/run_features.py first.")
        sys.exit(1)
        
    logger.info("Loading features...")
    df = pd.read_parquet(features_path)
    
    target_cols = ["pm25", "o3", "no2"]
    horizons = list(range(1, 25))  # 1 to 24 hours
    
    logger.info("Computing baselines...")
    for target in target_cols:
        if target in df.columns:
            df = add_persistence_baseline(df, target, horizons)
            df = add_seasonal_baseline(df, target)
            
    logger.info("Evaluating walk-forward metrics...")
    results = evaluate_baselines(df, target_cols, horizons)
    
    print("\n" + "="*50)
    print("Baseline Evaluation Results (MAE & RMSE)")
    print("="*50)
    
    for target, metrics in results.items():
        print(f"\nTarget: {target.upper()}")
        print("-" * 30)
        for model, scores in metrics.items():
            if scores["mae"] == 0.0:
                print(f"{model.capitalize():<12}: Insufficient data")
            else:
                print(f"{model.capitalize():<12}: MAE={scores['mae']:.2f} | RMSE={scores['rmse']:.2f}")
                
    # Save the baseline metrics
    output_path = data_dir / "features" / "baseline_metrics.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("metrics_saved", extra={"path": str(output_path)})

if __name__ == "__main__":
    main()
