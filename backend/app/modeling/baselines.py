"""Baseline models: Persistence and Seasonal Average."""

import pandas as pd


def add_persistence_baseline(
    df: pd.DataFrame, target_col: str, horizons: list[int]
) -> pd.DataFrame:
    """Adds persistence baseline predictions to df in-place.

    Persistence simply predicts the current value will remain the same at all horizons.
    Instead of shifting the prediction forward, we align the TRUE future values back to time t
    in the CV evaluation. So we just need to store the current value as the prediction.
    """
    for h in horizons:
        df[f"{target_col}_persist_{h}h"] = df[target_col]
    return df


def add_seasonal_baseline(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """Adds a seasonal average column to df in-place.

    Computes a 4-week rolling average for the specific station, day of week, and hour of day.
    Shifted by 1 so the current value is not included in its own average.

    Because the most recent data point for a specific (DOW, Hour) is exactly 1 week (168h) ago,
    this value is strictly leak-free for any forecast horizon < 168 hours. The value of `seasonal_avg`
    at time t+h was computed using only data <= t.
    """
    # Ensure sorted by time
    df = df.sort_values(["station_id", "ts"])

    # 4-week rolling mean of that exact hour/dow
    df[f"{target_col}_seasonal_avg"] = df.groupby(["station_id", "day_of_week", "hour_of_day"])[
        target_col
    ].transform(lambda x: x.rolling(4, min_periods=1).mean().shift(1))
    return df
