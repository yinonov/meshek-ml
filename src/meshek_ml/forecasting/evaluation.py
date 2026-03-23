"""Forecast evaluation metrics."""

from __future__ import annotations

import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Error."""
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def wmape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Weighted Mean Absolute Percentage Error.

    WMAPE = sum(|actual - predicted|) / sum(|actual|)
    Industry standard from M5 competition.
    """
    total_actual = np.sum(np.abs(actual))
    if total_actual == 0:
        return 0.0
    return float(np.sum(np.abs(actual - predicted)) / total_actual)


def pinball_loss(actual: np.ndarray, predicted: np.ndarray, quantile: float = 0.5) -> float:
    """Pinball (quantile) loss.

    Asymmetric loss that penalizes under/over-prediction differently
    based on the critical ratio tau = Cu / (Cu + Co).

    Args:
        actual: Actual demand values.
        predicted: Predicted quantile values.
        quantile: Target quantile (0 to 1). Higher = penalize understock more.

    Returns:
        Mean pinball loss.
    """
    error = actual - predicted
    loss = np.where(error >= 0, quantile * error, (quantile - 1) * error)
    return float(np.mean(loss))


def compute_all_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    quantile: float = 0.5,
) -> dict[str, float]:
    """Compute all forecasting metrics at once."""
    return {
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "wmape": wmape(actual, predicted),
        "pinball_loss": pinball_loss(actual, predicted, quantile),
    }
