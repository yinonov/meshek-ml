"""Shared test fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_dates():
    """A small date range for testing."""
    return pd.date_range("2024-01-01", "2024-01-31", freq="D")


@pytest.fixture
def sample_demand_df(sample_dates):
    """A minimal demand DataFrame for testing."""
    import numpy as np

    n = len(sample_dates)
    return pd.DataFrame(
        {
            "date": sample_dates,
            "merchant_id": "merchant_000",
            "product": "Tomatoes",
            "realized_demand": np.random.default_rng(42).integers(5, 30, size=n),
        }
    )


@pytest.fixture
def canonical_demand_df():
    """A demand DataFrame in the canonical forecasting schema."""
    import numpy as np

    dates = pd.date_range("2024-01-01", periods=90, freq="D")
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "date": dates,
            "merchant_id": "merchant_000",
            "product": "Tomatoes",
            "quantity": rng.integers(5, 30, size=90),
        }
    )
