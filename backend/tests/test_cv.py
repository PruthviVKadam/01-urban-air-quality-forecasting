"""Tests to ensure strictly ZERO leakage in cross-validation."""

import pandas as pd
from app.modeling.baselines import add_persistence_baseline, add_seasonal_baseline
from app.modeling.cv import evaluate_baselines


def test_no_leakage_in_seasonal_baseline() -> None:
    # 1. Create a synthetic dataset with an obvious pattern
    # Let's say PM2.5 is exactly equal to the day of the month
    dates = pd.date_range("2025-01-01", "2025-02-28", freq="1h")
    df = pd.DataFrame(
        {
            "station_id": ["s1"] * len(dates),
            "ts": dates,
            "day_of_week": dates.dayofweek,
            "hour_of_day": dates.hour,
            "pm25": dates.day,  # Values are 1 to 31
        }
    )

    target = "pm25"

    # 2. Apply baseline
    df = add_seasonal_baseline(df, target)

    # 3. Prove no leakage
    # Let's take a specific time: Jan 15th (Wednesday) 10:00 AM. (day=15)
    # The previous Wednesdays were:
    # - Jan 8th (day=8)
    # - Jan 1st (day=1)

    t_15 = df[(df["ts"].dt.day == 15) & (df["ts"].dt.hour == 10)].iloc[0]

    # The seasonal_avg for Wed 10:00 AM at Jan 15th should be the average of Jan 1st and Jan 8th!
    # Which is (1 + 8) / 2 = 4.5
    assert t_15["pm25_seasonal_avg"] == 4.5

    # Now let's say we are AT Jan 15th 10:00 AM, predicting 168 hours (1 week) ahead (Jan 22nd 10:00 AM)
    # The evaluation harness shifts `seasonal_avg` back by `h` hours.
    # Wait, the baseline logic for h=168 uses the `seasonal_avg` AT Jan 22nd 10:00 AM.
    t_22 = df[(df["ts"].dt.day == 22) & (df["ts"].dt.hour == 10)].iloc[0]

    # At Jan 22nd, the `seasonal_avg` is the average of Jan 1, Jan 8, Jan 15
    # Which is (1 + 8 + 15) / 3 = 8.0
    assert t_22["pm25_seasonal_avg"] == 8.0

    # Does the prediction for Jan 22nd made on Jan 15th leak?
    # At Jan 15th, 168 hours into the future is Jan 22nd.
    # The CV harness compares true value at Jan 22nd (which is 22)
    # to the `seasonal_pred_168h` which is the `seasonal_avg` at Jan 22nd (which is 8.0).
    # Since 8.0 was calculated entirely from data <= Jan 15th, there is ZERO leakage!
    # Even if we predicted h=24 (Jan 16th), the seasonal_avg at Jan 16th (Thursday)
    # only uses data from Jan 9th and Jan 2nd, which are strictly <= Jan 15th.

    # 4. Run the full CV harness to ensure it doesn't crash
    df = add_persistence_baseline(df, target, [1, 24])
    results = evaluate_baselines(df, [target], [1, 24])

    assert results["pm25"]["persistence"]["mae"] > 0
    assert results["pm25"]["seasonal"]["mae"] > 0
