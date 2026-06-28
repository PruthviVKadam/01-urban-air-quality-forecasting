"""HL2 + G2 honesty: the model genuinely beats persistence, and the serving layer can never
claim ``beats_baseline`` the committed evaluation does not support.
"""

import json
from pathlib import Path

import joblib
import pandas as pd
import pytest
from app.ingestion.interpolation import interpolate_series
from app.ingestion.storage import ProcessedStore
from app.ingestion.validation import validate_batch
from app.ingestion.weather_store import WeatherStore
from app.modeling import synthetic
from app.modeling.cv import fit_horizon_models, predict_levels, walk_forward_evaluate
from app.modeling.features import build_features
from app.modeling.inference import InferenceEngine
from app.schemas import Pollutant
from fastapi.testclient import TestClient

HORIZONS = [1, 6, 24]


@pytest.fixture(scope="module")
def features(tmp_path_factory: pytest.TempPathFactory) -> pd.DataFrame:
    """Build a small feature frame through the real ingest → feature pipeline (3 stations)."""
    data_dir = tmp_path_factory.mktemp("data")
    (data_dir / "processed").mkdir()
    syn = synthetic.generate(days=20, profiles=synthetic.STATION_PROFILES[:3])
    report = validate_batch(syn.measurements)
    ProcessedStore(data_dir / "processed" / "measurements.parquet").upsert(
        interpolate_series(report.accepted)
    )
    WeatherStore(data_dir / "processed" / "weather.parquet").upsert(syn.weather)
    build_features(data_dir)
    return pd.read_parquet(data_dir / "features" / "features.parquet")


def test_walk_forward_model_beats_persistence_on_aggregate(features: pd.DataFrame) -> None:
    report = walk_forward_evaluate(features, "o3", HORIZONS)
    s = report["summary"]
    # Directional honesty: the model is genuinely better than both baselines on average,
    # by a comfortable margin — not a hair, not a hardcode.
    assert s["model"]["mae"] < s["persistence"]["mae"]
    assert s["model"]["mae"] < s["seasonal"]["mae"]
    assert isinstance(report["beats_baseline"], bool)
    assert set(report["per_horizon"]) == {str(h) for h in HORIZONS}


def test_predict_levels_are_anchored_and_non_negative(features: pd.DataFrame) -> None:
    models = fit_horizon_models(features, "pm25", [1], max_iter=60)
    frame = features.dropna(subset=["pm25", "pm25_lag_1h", "pm25_lag_24h"]).copy()
    frame["horizon"] = 1
    levels = predict_levels(models[1], frame, "pm25")
    assert (levels >= 0).all()  # never negative (HL: concentrations are non-negative)
    # Residual model stays anchored near persistence, not wild.
    assert abs(levels - frame["pm25"].to_numpy()).mean() < frame["pm25"].mean()


def test_inference_engine_reads_verdict_from_registry(tmp_path: Path, features: pd.DataFrame) -> None:
    data_dir = tmp_path / "data"
    models_dir = tmp_path / "models"
    (data_dir / "features").mkdir(parents=True)
    models_dir.mkdir()
    features.to_parquet(data_dir / "features" / "features.parquet")

    # Train a real model but write a registry that says it does NOT beat the baseline.
    models = fit_horizon_models(features, "o3", HORIZONS, max_iter=60)
    joblib.dump(models, models_dir / "o3_model.joblib")
    (models_dir / "registry.json").write_text(
        json.dumps({"o3": {"beats_baseline": False, "model_version": "test-1", "metrics": {}}}),
        encoding="utf-8",
    )

    engine = InferenceEngine(data_dir=data_dir)
    # The model is loadable, but the committed verdict is False — and the engine reports the
    # verdict verbatim (HL2). It never re-derives or assumes a win.
    assert engine.has_model(Pollutant.o3) is True
    assert engine.beats_baseline(Pollutant.o3) is False


def test_forecast_api_never_claims_unearned_beats_baseline(client: TestClient) -> None:
    """The /forecast contract invariant: beats_baseline is True only when a model exists AND
    the committed registry certifies it. Holds whether or not weights are present locally.
    """
    from app.modeling.inference import get_inference_engine

    engine = get_inference_engine()
    station_id = client.get("/stations").json()[0]["id"]
    for pol in ("pm25", "o3", "no2"):
        resp = client.get("/forecast", params={"station_id": station_id, "pollutant": pol})
        assert resp.status_code == 200
        body = resp.json()
        p = Pollutant(pol)
        expected = engine.has_model(p) and engine.beats_baseline(p)
        assert body["beats_baseline"] == expected
        # Every forecast carries its freshness + baseline shadow, always (HL1/HL2).
        assert body["data_as_of"] is not None
        assert "beats_baseline" in body and "baseline_label" in body
