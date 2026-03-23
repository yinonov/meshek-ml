"""Tests for feature engineering."""

from meshek_ml.forecasting.features import add_calendar_features, add_lag_features


def test_add_calendar_features(sample_demand_df):
    result = add_calendar_features(sample_demand_df)
    assert "day_of_week" in result.columns
    assert "month" in result.columns
    assert "is_weekend" in result.columns
    assert "sin_annual" in result.columns


def test_add_lag_features(sample_demand_df):
    result = add_lag_features(sample_demand_df, lags=[1, 7])
    assert "lag_1" in result.columns
    assert "lag_7" in result.columns
