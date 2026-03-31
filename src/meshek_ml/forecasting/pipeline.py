"""Forecasting train/eval orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from meshek_ml.common.seed import set_global_seed
from meshek_ml.forecasting.evaluation import compute_all_metrics
from meshek_ml.forecasting.features import (
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
)
from meshek_ml.forecasting.schema import (
    normalize_simulation_data,
    validate_demand_schema,
)
from meshek_ml.forecasting.tree_models import train_lightgbm, train_xgboost

if TYPE_CHECKING:
    from meshek_ml.common.types import MetricsDict

TARGET_COL = "quantity"

FEATURE_COLS_TO_DROP = ["date", "merchant_id", "product", "quantity"]

MODEL_REGISTRY: dict[str, Any] = {
    "lightgbm": train_lightgbm,
    "xgboost": train_xgboost,
}


def run_forecast_pipeline(
    data: pd.DataFrame,
    model_type: str = "lightgbm",
    train_end_date: str = "2024-06-30",
    horizon: int = 7,
    seed: int = 42,
    return_predictions: bool = False,
) -> MetricsDict | tuple[MetricsDict, pd.Series]:
    """Run the full forecasting pipeline: validate, feature engineer, train, evaluate.

    Args:
        data: Demand data — either raw simulation output or canonical schema.
        model_type: One of 'lightgbm', 'xgboost'.
        train_end_date: Train/validation split date (inclusive for train).
        horizon: Forecast horizon in days (metadata only, not used in split).
        seed: Random seed for reproducibility.
        return_predictions: If True, also return the validation predictions
            as a pandas Series (for downstream use in optimization).

    Returns:
        If return_predictions is False: dict with keys mae, rmse, wmape, pinball_loss.
        If return_predictions is True: tuple of (metrics dict, predictions Series).

    Raises:
        SchemaValidationError: If data is missing required columns or has
            malformed values.
        ValueError: If no validation data remains after the time split.
    """
    set_global_seed(seed)

    df = data.copy()

    # Normalize simulation data to canonical schema (FORE-04)
    if "realized_demand" in df.columns:
        df = normalize_simulation_data(df)

    # Validate schema — fail fast on bad data (FORE-05)
    df = validate_demand_schema(df)

    # Ensure date is datetime and sort
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["merchant_id", "product", "date"]).reset_index(drop=True)

    # Feature engineering
    df = add_lag_features(df, target_col=TARGET_COL)
    df = add_rolling_features(df, target_col=TARGET_COL)
    df = add_calendar_features(df)

    # Time-based split (FORE-02)
    cutoff = pd.Timestamp(train_end_date)
    train = df[df["date"] <= cutoff].copy()
    val = df[df["date"] > cutoff].copy()

    # Drop NaN rows from lag/rolling features
    train = train.dropna()
    val = val.dropna()

    if len(val) == 0:
        raise ValueError(
            "No validation data after removing NaN rows. "
            "Check train_end_date or data range."
        )

    # Build feature matrices
    feature_cols = [c for c in train.columns if c not in FEATURE_COLS_TO_DROP]
    x_train = train[feature_cols]
    y_train = train[TARGET_COL].values
    x_val = val[feature_cols]
    y_val = val[TARGET_COL].values

    # Train model
    if model_type not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model_type: {model_type}. Choose from {list(MODEL_REGISTRY)}"
        )
    train_fn = MODEL_REGISTRY[model_type]
    model = train_fn(x_train, y_train)

    # Evaluate (FORE-03)
    predictions = model.predict(x_val)
    metrics = compute_all_metrics(y_val, predictions)

    if return_predictions:
        return metrics, pd.Series(predictions, index=val.index, name="predicted_demand")
    return metrics


def load_and_run(
    source: str = "synthetic",
    path: str | None = None,
    model_type: str = "lightgbm",
    train_end_date: str = "2024-06-30",
    seed: int = 42,
) -> tuple[pd.DataFrame, MetricsDict]:
    """Convenience wrapper: load data from source, run pipeline.

    Args:
        source: One of 'synthetic', 'csv', 'parquet'.
        path: File path (required for csv/parquet).
        model_type: Model to train.
        train_end_date: Train/validation split date.
        seed: Random seed.

    Returns:
        Tuple of (data DataFrame, metrics dict).
    """
    from meshek_ml.simulation.generator import run_simulation

    if source == "synthetic":
        data = run_simulation(
            n_merchants=3,
            start_date="2024-01-01",
            end_date="2024-12-31",
            seed=seed,
        )
    elif source == "csv":
        from meshek_ml.common.io import load_csv

        data = load_csv(path)
    elif source == "parquet":
        from meshek_ml.common.io import load_parquet

        data = load_parquet(path)
    else:
        raise ValueError(f"Unknown source: {source}. Choose from: synthetic, csv, parquet")

    metrics = run_forecast_pipeline(
        data, model_type=model_type, train_end_date=train_end_date, seed=seed
    )
    return data, metrics
