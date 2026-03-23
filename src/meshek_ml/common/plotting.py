"""Shared plotting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import pandas as pd


def plot_demand_series(
    df: pd.DataFrame,
    product_col: str = "product",
    demand_col: str = "demand",
    date_col: str = "date",
    title: str = "Daily Demand",
) -> plt.Figure:
    """Plot demand time series for one or more products."""
    fig, ax = plt.subplots(figsize=(12, 5))
    for product, group in df.groupby(product_col):
        ax.plot(group[date_col], group[demand_col], label=product, alpha=0.8)
    ax.set_xlabel("Date")
    ax.set_ylabel("Demand")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_forecast_vs_actual(
    actual: pd.Series,
    forecast: pd.Series,
    title: str = "Forecast vs Actual",
) -> plt.Figure:
    """Plot forecast against actual values."""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(actual.index, actual.values, label="Actual", color="black")
    ax.plot(forecast.index, forecast.values, label="Forecast", color="blue", linestyle="--")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig
