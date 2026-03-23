"""Tests for demand generation."""

import numpy as np
import pandas as pd

from meshek_ml.common.types import ProductCategory
from meshek_ml.simulation.demand import generate_demand
from meshek_ml.simulation.schemas import ProductSpec


def test_generate_demand_returns_correct_shape():
    dates = pd.date_range("2024-01-01", "2024-01-31", freq="D")
    product = ProductSpec(ProductCategory.TOMATOES, "Tomatoes", 20.0, 3.0, 6, 5.0, 7.0)
    df = generate_demand(product, dates, rng=np.random.default_rng(42))
    assert len(df) == len(dates)
    assert "realized_demand" in df.columns
    assert (df["realized_demand"] >= 0).all()


def test_generate_demand_respects_merchant_scale():
    dates = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    product = ProductSpec(ProductCategory.TOMATOES, "Tomatoes", 20.0, 3.0, 6, 5.0, 7.0)
    df_low = generate_demand(product, dates, merchant_scale=0.5, rng=np.random.default_rng(42))
    df_high = generate_demand(product, dates, merchant_scale=2.0, rng=np.random.default_rng(42))
    # Higher scale should produce higher mean demand on average
    assert df_high["adjusted_demand"].mean() > df_low["adjusted_demand"].mean()
