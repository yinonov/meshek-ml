"""Tests for forecast evaluation metrics."""

import numpy as np

from meshek_ml.forecasting.evaluation import mae, pinball_loss, rmse, wmape


def test_mae_perfect():
    actual = np.array([10, 20, 30])
    assert mae(actual, actual) == 0.0


def test_rmse_known():
    actual = np.array([10.0, 20.0])
    predicted = np.array([12.0, 18.0])
    assert abs(rmse(actual, predicted) - 2.0) < 1e-6


def test_wmape_known():
    actual = np.array([100.0, 200.0])
    predicted = np.array([110.0, 190.0])
    # WMAPE = (10 + 10) / (100 + 200) = 20/300
    assert abs(wmape(actual, predicted) - 20 / 300) < 1e-6


def test_pinball_loss_symmetric():
    actual = np.array([10.0, 20.0])
    predicted = np.array([10.0, 20.0])
    assert pinball_loss(actual, predicted, quantile=0.5) == 0.0
