"""Feature engineering for demand forecasting."""

from __future__ import annotations

import numpy as np
import pandas as pd


def add_lag_features(
    df: pd.DataFrame,
    target_col: str = "realized_demand",
    lags: list[int] | None = None,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Add lag features to a demand DataFrame.

    Args:
        df: Input DataFrame sorted by date.
        target_col: Column to create lags from.
        lags: List of lag periods. Defaults to [1, 7, 14, 28].
        group_cols: Columns to group by before computing lags.

    Returns:
        DataFrame with lag columns added.
    """
    if lags is None:
        lags = [1, 7, 14, 28]
    if group_cols is None:
        group_cols = ["merchant_id", "product"]

    df = df.copy()
    grouped = df.groupby(group_cols)[target_col]
    for lag in lags:
        df[f"lag_{lag}"] = grouped.shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame,
    target_col: str = "realized_demand",
    windows: list[int] | None = None,
    group_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Add rolling mean and std features.

    Args:
        df: Input DataFrame sorted by date.
        target_col: Column to compute rolling stats from.
        windows: List of window sizes. Defaults to [7, 14, 28].
        group_cols: Columns to group by.

    Returns:
        DataFrame with rolling feature columns added.
    """
    if windows is None:
        windows = [7, 14, 28]
    if group_cols is None:
        group_cols = ["merchant_id", "product"]

    df = df.copy()
    grouped = df.groupby(group_cols)[target_col]
    for w in windows:
        window_size = w  # Bind loop variable for lambda
        df[f"rolling_mean_{w}"] = grouped.transform(
            lambda x, ws=window_size: x.shift(1).rolling(ws).mean()
        )
        df[f"rolling_std_{w}"] = grouped.transform(
            lambda x, ws=window_size: x.shift(1).rolling(ws).std()
        )
    return df


def add_calendar_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """Add calendar-based features.

    Args:
        df: Input DataFrame with a date column.
        date_col: Name of the date column.

    Returns:
        DataFrame with calendar feature columns added.
    """
    df = df.copy()
    dt = pd.to_datetime(df[date_col])
    df["day_of_week"] = dt.dt.dayofweek
    df["day_of_month"] = dt.dt.day
    df["month"] = dt.dt.month
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)

    # Fourier terms for annual seasonality
    day_of_year = dt.dt.dayofyear
    df["sin_annual"] = np.sin(2 * np.pi * day_of_year / 365.25)
    df["cos_annual"] = np.cos(2 * np.pi * day_of_year / 365.25)

    return df
