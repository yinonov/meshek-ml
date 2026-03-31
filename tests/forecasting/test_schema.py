"""Tests for demand schema validation."""

import pandas as pd
import pytest

from meshek_ml.forecasting.schema import (
    REQUIRED_COLUMNS,
    SchemaValidationError,
    normalize_simulation_data,
    validate_demand_schema,
)


def _make_valid_df(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=n),
            "merchant_id": "m1",
            "product": "Tomatoes",
            "quantity": range(n),
        }
    )


class TestValidateDemandSchema:
    def test_valid_df_passes(self):
        df = _make_valid_df()
        result = validate_demand_schema(df)
        assert list(result.columns) == list(df.columns)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_missing_quantity_raises(self):
        df = _make_valid_df().drop(columns=["quantity"])
        with pytest.raises(SchemaValidationError, match="quantity"):
            validate_demand_schema(df)

    def test_missing_multiple_columns_raises(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "extra": [1]})
        with pytest.raises(SchemaValidationError, match="Missing required columns"):
            validate_demand_schema(df)

    def test_unparseable_date_raises(self):
        df = _make_valid_df()
        df["date"] = "not-a-date"
        with pytest.raises(SchemaValidationError, match="date"):
            validate_demand_schema(df)

    def test_null_values_raises(self):
        df = _make_valid_df()
        df.loc[0, "quantity"] = None
        with pytest.raises(SchemaValidationError, match="Null values found"):
            validate_demand_schema(df)

    def test_required_columns_constant(self):
        assert REQUIRED_COLUMNS == ["date", "merchant_id", "product", "quantity"]


class TestNormalizeSimulationData:
    def test_renames_realized_demand(self):
        df = pd.DataFrame(
            {
                "date": ["2024-01-01"],
                "merchant_id": ["m1"],
                "product": ["Tomatoes"],
                "realized_demand": [10],
                "base_demand": [8],
                "seasonal_factor": [1.0],
                "weekly_factor": [1.0],
                "holiday_factor": [1.0],
                "adjusted_demand": [8],
            }
        )
        result = normalize_simulation_data(df)
        assert "quantity" in result.columns
        assert "realized_demand" not in result.columns
        assert "base_demand" not in result.columns

    def test_missing_realized_demand_raises(self):
        df = pd.DataFrame({"date": ["2024-01-01"], "quantity": [10]})
        with pytest.raises(KeyError, match="realized_demand"):
            normalize_simulation_data(df)
