"""Tests for the forecasting pipeline orchestrator."""

import pandas as pd
import pytest

from meshek_ml.forecasting.pipeline import run_forecast_pipeline
from meshek_ml.forecasting.schema import SchemaValidationError


@pytest.mark.slow
def test_pipeline_end_to_end():
    """Full pipeline: synthetic data -> LightGBM -> metrics."""
    from meshek_ml.simulation.generator import run_simulation

    data = run_simulation(
        n_merchants=1,
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed=42,
    )
    metrics = run_forecast_pipeline(data, train_end_date="2024-09-30", seed=42)

    assert isinstance(metrics, dict)
    for key in ["mae", "rmse", "wmape", "pinball_loss"]:
        assert key in metrics, f"Missing metric: {key}"
        assert isinstance(metrics[key], float)
        assert metrics[key] >= 0


def test_pipeline_rejects_bad_schema():
    """Pipeline fails fast when required columns are missing."""
    df = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10),
            "merchant_id": "m1",
            "product": "Tomatoes",
            # Missing 'quantity' column
        }
    )
    with pytest.raises(SchemaValidationError, match="quantity"):
        run_forecast_pipeline(df)


@pytest.mark.slow
def test_pipeline_time_split():
    """Pipeline uses time-based split without error."""
    from meshek_ml.simulation.generator import run_simulation

    data = run_simulation(
        n_merchants=1,
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed=42,
    )
    metrics = run_forecast_pipeline(data, train_end_date="2024-06-30", seed=42)
    assert isinstance(metrics, dict)
    assert len(metrics) == 4


@pytest.mark.slow
def test_pipeline_xgboost():
    """Pipeline works with XGBoost model type."""
    from meshek_ml.simulation.generator import run_simulation

    data = run_simulation(
        n_merchants=1,
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed=42,
    )
    metrics = run_forecast_pipeline(
        data, model_type="xgboost", train_end_date="2024-09-30", seed=42
    )
    assert isinstance(metrics, dict)
    for key in ["mae", "rmse", "wmape", "pinball_loss"]:
        assert key in metrics


@pytest.mark.slow
def test_pipeline_normalizes_simulation_data():
    """Pipeline normalizes simulation data (realized_demand -> quantity)."""
    from meshek_ml.simulation.generator import run_simulation

    data = run_simulation(
        n_merchants=1,
        start_date="2024-01-01",
        end_date="2024-12-31",
        seed=42,
    )
    # Raw simulation data has 'realized_demand', not 'quantity'
    assert "realized_demand" in data.columns
    assert "quantity" not in data.columns

    # Pipeline should normalize and succeed
    metrics = run_forecast_pipeline(data, train_end_date="2024-09-30", seed=42)
    assert isinstance(metrics, dict)
    assert all(v >= 0 for v in metrics.values())
