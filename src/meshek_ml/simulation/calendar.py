"""Seasonality, weekly patterns, and Israeli holiday calendar."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd


def weekly_factors(
    dates: pd.DatetimeIndex,
    pattern: dict[str, float] | None = None,
) -> np.ndarray:
    """Compute day-of-week multiplicative factors for a date range.

    Args:
        dates: DatetimeIndex of dates.
        pattern: Mapping of day name to multiplier. Defaults to typical greengrocer pattern.

    Returns:
        Array of multiplicative factors, one per date.
    """
    if pattern is None:
        pattern = {
            "Monday": 0.85,
            "Tuesday": 0.90,
            "Wednesday": 0.95,
            "Thursday": 1.00,
            "Friday": 1.15,
            "Saturday": 1.30,
            "Sunday": 0.70,
        }
    return np.array([pattern.get(d.day_name(), 1.0) for d in dates])


def annual_seasonality(
    dates: pd.DatetimeIndex,
    amplitude: float = 0.3,
    peak_day: int = 180,
) -> np.ndarray:
    """Compute annual seasonality using Fourier terms.

    Args:
        dates: DatetimeIndex of dates.
        amplitude: Strength of seasonal effect (0 = no seasonality, 1 = full swing).
        peak_day: Day of year with peak demand (180 = ~July for summer fruits).

    Returns:
        Array of multiplicative factors centered around 1.0.
    """
    day_of_year = dates.dayofyear.values
    phase = 2 * np.pi * (day_of_year - peak_day) / 365.25
    return 1.0 + amplitude * np.cos(phase)


def israeli_holidays(year: int) -> list[tuple[date, str, float]]:
    """Return approximate Israeli holiday dates with demand multipliers.

    Uses fixed Gregorian approximations. For production use, integrate
    a Hebrew calendar library.

    Args:
        year: Calendar year.

    Returns:
        List of (date, holiday_name, demand_multiplier) tuples.
    """
    # Approximate Gregorian dates for major Israeli holidays
    # These shift each year; this provides reasonable defaults
    holidays = [
        (date(year, 3, 25), "Pesach", 1.8),
        (date(year, 3, 26), "Pesach", 1.5),
        (date(year, 4, 1), "Pesach_end", 1.4),
        (date(year, 5, 14), "Yom_Haatzmaut", 1.6),
        (date(year, 6, 5), "Shavuot", 1.5),
        (date(year, 9, 16), "Rosh_Hashana", 2.0),
        (date(year, 9, 17), "Rosh_Hashana", 1.8),
        (date(year, 9, 25), "Yom_Kippur_eve", 1.5),
        (date(year, 9, 30), "Sukkot", 1.7),
        (date(year, 10, 1), "Sukkot", 1.5),
        (date(year, 12, 15), "Hanukkah", 1.3),
    ]
    return [(d, name, mult) for d, name, mult in holidays if d.year == year]


def holiday_factors(dates: pd.DatetimeIndex) -> np.ndarray:
    """Compute holiday multiplicative factors for a date range.

    Args:
        dates: DatetimeIndex of dates.

    Returns:
        Array of multiplicative factors (1.0 for non-holidays).
    """
    factors = np.ones(len(dates))
    years = sorted(set(dates.year))

    holiday_map: dict[date, float] = {}
    for year in years:
        for d, _name, mult in israeli_holidays(year):
            holiday_map[d] = mult
            # Add pre-holiday shopping boost
            pre_holiday = d - timedelta(days=1)
            if pre_holiday not in holiday_map:
                holiday_map[pre_holiday] = 1.0 + (mult - 1.0) * 0.5

    for i, dt in enumerate(dates):
        d = dt.date() if hasattr(dt, "date") else dt
        if d in holiday_map:
            factors[i] = holiday_map[d]

    return factors
