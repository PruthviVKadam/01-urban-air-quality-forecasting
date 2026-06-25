"""Metrics for Exceedance Events."""

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score

# Thresholds for Unhealthy for Sensitive Groups (USG)
# Source: US EPA AQI breakpoints
EXCEEDANCE_THRESHOLDS = {
    "pm25": 35.4,  # > 35.4 µg/m³
    "o3": 70.0,  # > 70 ppb (8-hour average, but we'll use it as a rough hourly threshold here)
    "no2": 100.0,  # > 100 ppb
}


def calculate_exceedance_metrics(
    y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series, pollutant: str
) -> dict[str, float]:
    """Calculates precision, recall, and F1 score for exceedance events."""
    threshold = EXCEEDANCE_THRESHOLDS.get(pollutant)

    if threshold is None:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    y_true_binary = (y_true > threshold).astype(int)
    y_pred_binary = (y_pred > threshold).astype(int)

    # If there are no positive events in truth and no positive predictions, metrics are undefined.
    # We return 0.0, but zero_division=0 handles warnings.
    precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)

    return {"precision": float(precision), "recall": float(recall), "f1": float(f1)}
