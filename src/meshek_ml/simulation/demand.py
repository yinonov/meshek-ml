"""Demand generation using Negative Binomial and Poisson distributions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from meshek_ml.simulation.calendar import annual_seasonality, holiday_factors, weekly_factors
from meshek_ml.simulation.schemas import ProductSpec


def generate_demand(
    product: ProductSpec,
    dates: pd.DatetimeIndex,
    merchant_scale: float = 1.0,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Generate daily demand for a single product at a single merchant.

    Uses multiplicative seasonality model:
        adjusted_demand = base_mean * seasonal * weekly * holiday * merchant_scale
        realized_demand ~ NegBin(dispersion, adjusted_demand)

    Args:
        product: Product specification with demand parameters.
        dates: Date range for generation.
        merchant_scale: Multiplicative scale factor for the merchant.
        rng: NumPy random generator for reproducibility.

    Returns:
        DataFrame with columns: date, base_demand, seasonal_factor, weekly_factor,
        holiday_factor, adjusted_demand, realized_demand.
    """
    if rng is None:
        rng = np.random.default_rng()

    peak_day = (product.peak_month - 1) * 30 + 15 if product.peak_month else 180
    seasonal = annual_seasonality(dates, amplitude=product.seasonal_amplitude, peak_day=peak_day)
    weekly = weekly_factors(dates)
    holidays = holiday_factors(dates)

    adjusted = product.base_demand_mean * seasonal * weekly * holidays * merchant_scale
    adjusted = np.maximum(adjusted, 0.1)  # Avoid zero mean

    # Negative Binomial: parameterize by mean and dispersion
    n = product.dispersion
    p = n / (n + adjusted)
    realized = rng.negative_binomial(n=n, p=p)

    return pd.DataFrame(
        {
            "date": dates,
            "base_demand": product.base_demand_mean,
            "seasonal_factor": seasonal,
            "weekly_factor": weekly,
            "holiday_factor": holidays,
            "adjusted_demand": adjusted,
            "realized_demand": realized,
        }
    )
