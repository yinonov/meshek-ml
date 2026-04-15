# tests/recommendation/test_model_bundle.py
# Regression tests for the LightGBM model bundle pipeline -- D-14, D-15.
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from meshek_ml.recommendation.model_io import load_model_bundle
from meshek_ml.recommendation.training import train_and_save
from meshek_ml.simulation.generator import run_simulation

_FAST_PARAMS = {"n_estimators": 20, "num_leaves": 7, "verbose": -1}

_EXPECTED_FEATURE_COLS = [
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_std_7",
    "rolling_mean_14", "rolling_std_14",
    "rolling_mean_28", "rolling_std_28",
    "day_of_week", "day_of_month", "month", "week_of_year",
    "is_weekend", "sin_annual", "cos_annual",
]


def _patch_fast():
    """Patch LGBMRegressor globally so training runs fast.

    tree_models.py does ``import lightgbm as lgb`` locally inside
    train_lightgbm(), so lgb is not a module-level attribute. We patch
    the canonical ``lightgbm.LGBMRegressor`` which is what that local
    ``lgb.LGBMRegressor`` resolves to at call time.
    """
    import lightgbm as lgb

    _real_cls = lgb.LGBMRegressor

    return patch(
        "lightgbm.LGBMRegressor",
        side_effect=lambda **kw: _real_cls(**{**kw, **_FAST_PARAMS}),
    )


@pytest.fixture
def tiny_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    data = run_simulation(
        n_merchants=5, start_date="2024-01-01", end_date="2024-01-30", seed=42
    )
    with _patch_fast():
        bundle = train_and_save(tmp_path / "lightgbm_v1.bundle", data)
    return bundle, tmp_path, data


def test_bundle_round_trips(tiny_bundle):
    bundle, tmp_path, _ = tiny_bundle
    loaded = load_model_bundle(tmp_path / "lightgbm_v1.bundle")
    assert set(loaded.keys()) == {"model", "residual_std", "feature_cols"}


def test_feature_cols_present(tiny_bundle):
    bundle, _, _ = tiny_bundle
    assert bundle["feature_cols"], "feature_cols must not be empty"
    assert bundle["feature_cols"] == _EXPECTED_FEATURE_COLS


def test_residual_std_positive(tiny_bundle):
    bundle, _, _ = tiny_bundle
    assert bundle["residual_std"] > 0


def test_predict_shape(tiny_bundle):
    bundle, _, _ = tiny_bundle
    x = pd.DataFrame([{c: 0.0 for c in bundle["feature_cols"]}])
    arr = np.asarray(bundle["model"].predict(x))
    assert arr.shape == (1,)
    assert np.isfinite(arr[0])


def test_cli_produces_loadable_bundle(tmp_path, monkeypatch, capsys):
    """CLI main() invoked in-process produces a loadable bundle and JSON summary."""
    import meshek_ml.recommendation.cli_train as cli_train

    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bundle_path = tmp_path / "lightgbm_v1.bundle"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli_train",
            "--output", str(bundle_path),
            "--n-merchants", "5",
            "--days", "30",
            "--seed", "42",
        ],
    )

    with _patch_fast():
        cli_train.main()

    captured = capsys.readouterr()
    lines = [ln for ln in captured.out.strip().splitlines() if ln.strip()]
    assert lines, "cli_train.main() produced no stdout output"

    summary = json.loads(lines[-1])
    assert "bundle_path" in summary
    assert Path(summary["bundle_path"]).is_relative_to(tmp_path) or str(tmp_path) in summary["bundle_path"]
    assert summary["feature_count"] > 0
    assert summary["residual_std"] > 0
    assert summary["row_count"] > 0
    assert summary["seed"] == 42
    assert summary["n_merchants"] == 5
    assert summary["days"] == 30

    # Round-trip the bundle through load_model_bundle
    loaded = load_model_bundle(bundle_path)
    assert set(loaded.keys()) == {"model", "residual_std", "feature_cols"}
    assert loaded["feature_cols"], "feature_cols must not be empty"
    assert loaded["residual_std"] > 0

    # predict shape
    x = pd.DataFrame([{c: 0.0 for c in loaded["feature_cols"]}])
    arr = np.asarray(loaded["model"].predict(x))
    assert arr.shape == (1,)
    assert np.isfinite(arr[0])


def test_deterministic_rerun(tmp_path, monkeypatch):
    """Two train_and_save calls on the same DataFrame produce identical bundles (D-11)."""
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    data = run_simulation(
        n_merchants=5, start_date="2024-01-01", end_date="2024-01-30", seed=42
    )
    with _patch_fast():
        b1 = train_and_save(tmp_path / "run1.bundle", data)
    with _patch_fast():
        b2 = train_and_save(tmp_path / "run2.bundle", data)

    assert b1["feature_cols"] == b2["feature_cols"]
    assert abs(b1["residual_std"] - b2["residual_std"]) <= 1e-6
