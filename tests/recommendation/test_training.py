"""Tests for the offline LightGBM training entry point (06-03 Task 1)."""
from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest

from meshek_ml.recommendation.model_io import load_model_bundle
from meshek_ml.recommendation.training import train_and_save
from meshek_ml.simulation.generator import run_simulation


@pytest.fixture(scope="module")
def _synthetic_data():
    return run_simulation(
        n_merchants=3,
        start_date="2024-01-01",
        end_date="2024-03-31",
        seed=42,
    )


@pytest.mark.integration
def test_train_and_save_bundle_keys(tmp_path, monkeypatch, _synthetic_data):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    train_and_save(tmp_path / "m.bundle", _synthetic_data)
    loaded = load_model_bundle(tmp_path / "m.bundle")
    assert set(loaded.keys()) == {"model", "residual_std", "feature_cols"}


@pytest.mark.integration
def test_model_predicts_finite(tmp_path, monkeypatch, _synthetic_data):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bundle = train_and_save(tmp_path / "m.bundle", _synthetic_data)
    feature_cols = bundle["feature_cols"]
    # Build a tiny sample matrix filled with zeros and predict.
    import pandas as pd
    x = pd.DataFrame(
        [{c: 0.0 for c in feature_cols} for _ in range(3)]
    )
    preds = bundle["model"].predict(x)
    arr = np.asarray(preds)
    assert arr.shape[0] == 3
    assert np.all(np.isfinite(arr))


@pytest.mark.integration
def test_residual_std_positive(tmp_path, monkeypatch, _synthetic_data):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bundle = train_and_save(tmp_path / "m.bundle", _synthetic_data)
    assert bundle["residual_std"] > 0


@pytest.mark.integration
def test_feature_cols_excludes_targets(tmp_path, monkeypatch, _synthetic_data):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bundle = train_and_save(tmp_path / "m.bundle", _synthetic_data)
    feature_cols = bundle["feature_cols"]
    assert feature_cols, "feature_cols must be non-empty"
    forbidden = {"date", "merchant_id", "product", "quantity"}
    assert forbidden.isdisjoint(set(feature_cols))


def test_pipeline_public_api_untouched():
    """forecasting.pipeline.run_forecast_pipeline signature must be frozen."""
    from meshek_ml.forecasting.pipeline import run_forecast_pipeline

    sig = inspect.signature(run_forecast_pipeline)
    assert list(sig.parameters.keys()) == [
        "data",
        "model_type",
        "train_end_date",
        "horizon",
        "seed",
        "return_predictions",
    ]
