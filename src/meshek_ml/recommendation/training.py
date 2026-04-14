"""Offline LightGBM training entry point for Tier 3 inference (REC-03).

This module is the ONLY place where a LightGBM model is trained and
persisted for the recommendation service. It deliberately does NOT call
``forecasting.pipeline.run_forecast_pipeline`` (that function is a
train+evaluate harness with its own validation split) and it does not
modify ``forecasting.pipeline``'s public API. Instead we reuse the
low-level ``forecasting.features.*`` feature engineering helpers so the
training-time feature set is bit-for-bit identical to the inference-time
feature set (no train/serve skew).

The resulting ``ModelBundle`` is written via ``save_model_bundle``, which
enforces the path-traversal guard (T-6-08).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from meshek_ml.forecasting.features import (
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
)
from meshek_ml.forecasting.schema import (
    normalize_simulation_data,
    validate_demand_schema,
)
from meshek_ml.forecasting.tree_models import train_lightgbm
from meshek_ml.recommendation.model_io import ModelBundle, save_model_bundle

# Mirrored constants from forecasting.pipeline — kept inline so this module
# does NOT import from pipeline.py and therefore cannot accidentally couple
# to its train+eval behaviour.
TARGET_COL = "quantity"
FEATURE_COLS_TO_DROP = ["date", "merchant_id", "product", "quantity"]


def train_and_save(output_path: Path, data: pd.DataFrame) -> ModelBundle:
    """Train a LightGBM regressor on ``data`` and persist a ``ModelBundle``.

    Args:
        output_path: Destination path for the joblib-serialised bundle.
            Must resolve inside ``MESHEK_MODELS_DIR`` (or DEFAULT_MODELS_DIR).
        data: Canonical demand DataFrame OR raw simulation output (detected
            by the presence of ``realized_demand``).

    Returns:
        The ``ModelBundle`` dict that was just written.

    Raises:
        ValueError: if no training rows remain after feature-engineering
            dropna, or if ``output_path`` escapes the allowed models root.
    """
    df = data.copy()
    if "realized_demand" in df.columns:
        df = normalize_simulation_data(df)
    df = validate_demand_schema(df)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["merchant_id", "product", "date"]).reset_index(drop=True)
    df = add_lag_features(df, target_col=TARGET_COL)
    df = add_rolling_features(df, target_col=TARGET_COL)
    df = add_calendar_features(df)
    df = df.dropna()
    if df.empty:
        raise ValueError(
            "No training rows remain after feature engineering dropna; "
            "need more history."
        )
    feature_cols = [c for c in df.columns if c not in FEATURE_COLS_TO_DROP]
    x_train = df[feature_cols]
    y_train = df[TARGET_COL].to_numpy()
    model = train_lightgbm(x_train, y_train)
    residual_std = float(np.std(y_train - model.predict(x_train)))
    bundle: ModelBundle = {
        "model": model,
        "residual_std": residual_std,
        "feature_cols": feature_cols,
    }
    save_model_bundle(bundle, output_path)
    return bundle
