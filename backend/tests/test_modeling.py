"""Tests for Phase 3 ML metrics and modeling utilities."""

import numpy as np
from app.modeling.metrics import calculate_exceedance_metrics


def test_calculate_exceedance_metrics() -> None:
    # 1. PM2.5 threshold is 35.4
    target = "pm25"

    # Create synthetic true values: 3 safe, 2 exceeding
    y_true = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

    # Create synthetic predictions:
    # 10 -> 15 (TN)
    # 20 -> 36 (FP)
    # 30 -> 34 (TN)
    # 40 -> 36 (TP)
    # 50 -> 30 (FN)
    y_pred = np.array([15.0, 36.0, 34.0, 36.0, 30.0])

    metrics = calculate_exceedance_metrics(y_true, y_pred, target)

    # True Positives: 1 (the 40->36 case)
    # False Positives: 1 (the 20->36 case)
    # False Negatives: 1 (the 50->30 case)
    # True Negatives: 2

    # Precision = TP / (TP + FP) = 1 / 2 = 0.5
    # Recall = TP / (TP + FN) = 1 / 2 = 0.5

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5


def test_exceedance_metrics_no_positive_cases() -> None:
    y_true = np.array([10.0, 20.0])
    y_pred = np.array([10.0, 20.0])

    metrics = calculate_exceedance_metrics(y_true, y_pred, "pm25")
    assert metrics["precision"] == 0.0
    assert metrics["recall"] == 0.0
    assert metrics["f1"] == 0.0
