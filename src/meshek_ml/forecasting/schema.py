"""Canonical schema validation for demand forecasting data."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ["date", "merchant_id", "product", "quantity"]

SIMULATION_ONLY_COLUMNS = [
    "base_demand",
    "seasonal_factor",
    "weekly_factor",
    "holiday_factor",
    "adjusted_demand",
]


class SchemaValidationError(ValueError):
    """Raised when input data does not match the required forecasting schema."""


def validate_demand_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Validate that a DataFrame has the required columns for forecasting.

    Args:
        df: Input DataFrame to validate.

    Returns:
        The DataFrame with date column coerced to datetime.

    Raises:
        SchemaValidationError: If required columns are missing, dates are
            unparseable, or nulls exist in required columns.
    """
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise SchemaValidationError(f"Missing required columns: {missing}")

    try:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
    except Exception as exc:
        raise SchemaValidationError(
            "Column 'date' contains unparseable values"
        ) from exc

    nulls = {
        c: int(df[c].isna().sum())
        for c in REQUIRED_COLUMNS
        if df[c].isna().any()
    }
    if nulls:
        raise SchemaValidationError(f"Null values found: {nulls}")

    return df


def normalize_simulation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize simulation output to the canonical forecasting schema.

    Renames ``realized_demand`` to ``quantity`` and drops simulation-only
    columns so the data can enter the shared pipeline code path.

    Args:
        df: Raw simulation output from ``run_simulation()``.

    Returns:
        DataFrame with canonical columns.

    Raises:
        KeyError: If ``realized_demand`` column is not present.
    """
    if "realized_demand" not in df.columns:
        raise KeyError("Column 'realized_demand' not found in DataFrame")

    df = df.rename(columns={"realized_demand": "quantity"})
    df = df.drop(columns=SIMULATION_ONLY_COLUMNS, errors="ignore")
    return df
