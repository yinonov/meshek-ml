"""Forecasting train/eval orchestrator."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

    from meshek_ml.common.types import MetricsDict


def run_forecast_pipeline(
    data: pd.DataFrame,
    model_type: str = "lightgbm",
    train_end_date: str = "2024-06-30",
    horizon: int = 7,
) -> MetricsDict:
    """Run the full forecasting pipeline: feature engineering, train, evaluate.

    Args:
        data: Synthetic data from simulation.
        model_type: One of 'prophet', 'lightgbm', 'xgboost'.
        train_end_date: Train/test split date.
        horizon: Forecast horizon in days.

    Returns:
        Dictionary of evaluation metrics.
    """
    # TODO: Implement full pipeline
    raise NotImplementedError("Forecasting pipeline not yet implemented")
