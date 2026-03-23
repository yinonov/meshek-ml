"""Darts TimeSeries conversion utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def df_to_timeseries(
    df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "realized_demand",
    freq: str = "D",
):
    """Convert a pandas DataFrame to a Darts TimeSeries.

    Args:
        df: DataFrame with date and value columns.
        date_col: Date column name.
        value_col: Value column name.
        freq: Time series frequency.

    Returns:
        Darts TimeSeries object.
    """
    from darts import TimeSeries

    return TimeSeries.from_dataframe(df, time_col=date_col, value_cols=value_col, freq=freq)


def timeseries_to_df(ts, date_col: str = "date") -> pd.DataFrame:
    """Convert a Darts TimeSeries back to a pandas DataFrame.

    Args:
        ts: Darts TimeSeries object.
        date_col: Name for the date column in output.

    Returns:
        pandas DataFrame.
    """
    return ts.pd_dataframe().reset_index().rename(columns={"time": date_col})
