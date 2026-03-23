"""LightGBM and XGBoost forecast model wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd


def train_lightgbm(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    params: dict[str, Any] | None = None,
) -> Any:
    """Train a LightGBM regressor for demand forecasting.

    Args:
        x_train: Feature matrix.
        y_train: Target values.
        params: LightGBM parameters. Defaults to sensible values for demand forecasting.

    Returns:
        Trained LGBMRegressor model.
    """
    import lightgbm as lgb

    default_params = {
        "objective": "regression",
        "metric": "mae",
        "n_estimators": 500,
        "learning_rate": 0.05,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbose": -1,
    }
    if params:
        default_params.update(params)

    model = lgb.LGBMRegressor(**default_params)
    model.fit(x_train, y_train)
    return model


def train_xgboost(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    params: dict[str, Any] | None = None,
) -> Any:
    """Train an XGBoost regressor for demand forecasting.

    Args:
        x_train: Feature matrix.
        y_train: Target values.
        params: XGBoost parameters.

    Returns:
        Trained XGBRegressor model.
    """
    import xgboost as xgb

    default_params = {
        "objective": "reg:squarederror",
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "verbosity": 0,
    }
    if params:
        default_params.update(params)

    model = xgb.XGBRegressor(**default_params)
    model.fit(x_train, y_train)
    return model
