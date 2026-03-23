"""Prophet forecast model wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def create_prophet_forecast(
    train_df: pd.DataFrame,
    horizon_days: int = 7,
    date_col: str = "date",
    target_col: str = "realized_demand",
) -> pd.DataFrame:
    """Train Prophet and generate forecasts.

    Args:
        train_df: Training data with date and target columns.
        horizon_days: Number of days to forecast.
        date_col: Date column name.
        target_col: Target column name.

    Returns:
        DataFrame with Prophet forecast components (ds, yhat, yhat_lower, yhat_upper).
    """
    from prophet import Prophet

    prophet_df = train_df[[date_col, target_col]].rename(columns={date_col: "ds", target_col: "y"})

    model = Prophet(
        seasonality_mode="multiplicative",
        weekly_seasonality=True,
        yearly_seasonality=True,
    )
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=horizon_days)
    forecast = model.predict(future)

    return forecast
