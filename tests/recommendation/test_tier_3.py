"""Tests for tier_3_ml_forecast (REC-03, INFRA-01)."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from meshek_ml.recommendation.tiers import tier_3_ml_forecast
from meshek_ml.storage import MerchantStore


@pytest.mark.integration
def test_reasoning_tier_is_ml_forecast(
    trained_model_bundle, merchant_store_factory
):
    merchant_store_factory("tier3a", days=30)
    with MerchantStore("tier3a", must_exist=True) as store:
        sales = store.read_sales()
    resp = tier_3_ml_forecast(
        merchant_id="tier3a",
        sales=sales,
        model=trained_model_bundle["model"],
        residual_std=trained_model_bundle["residual_std"],
        feature_cols=trained_model_bundle["feature_cols"],
    )
    assert resp.recommendations[0].reasoning_tier == "ml_forecast"
    assert resp.merchant_id == "tier3a"


@pytest.mark.integration
def test_confidence_bounds(trained_model_bundle, merchant_store_factory):
    merchant_store_factory("tier3b", days=30)
    with MerchantStore("tier3b", must_exist=True) as store:
        sales = store.read_sales()
    resp = tier_3_ml_forecast(
        merchant_id="tier3b",
        sales=sales,
        model=trained_model_bundle["model"],
        residual_std=trained_model_bundle["residual_std"],
        feature_cols=trained_model_bundle["feature_cols"],
    )
    assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95


@pytest.mark.integration
def test_predicted_demand_non_negative(trained_model_bundle, merchant_store_factory):
    merchant_store_factory("tier3c", days=30)
    with MerchantStore("tier3c", must_exist=True) as store:
        sales = store.read_sales()
    resp = tier_3_ml_forecast(
        merchant_id="tier3c",
        sales=sales,
        model=trained_model_bundle["model"],
        residual_std=trained_model_bundle["residual_std"],
        feature_cols=trained_model_bundle["feature_cols"],
    )
    for rec in resp.recommendations:
        assert rec.predicted_demand >= 0


@pytest.mark.integration
def test_one_rec_per_product(trained_model_bundle, merchant_store_factory):
    products = ["tomato", "cucumber", "onion"]
    merchant_store_factory("tier3d", days=30, products=products)
    with MerchantStore("tier3d", must_exist=True) as store:
        sales = store.read_sales()
    resp = tier_3_ml_forecast(
        merchant_id="tier3d",
        sales=sales,
        model=trained_model_bundle["model"],
        residual_std=trained_model_bundle["residual_std"],
        feature_cols=trained_model_bundle["feature_cols"],
    )
    assert len(resp.recommendations) == len(set(sales["product"]))
    assert {r.product_id for r in resp.recommendations} == set(products)


def test_negative_prediction_clamped_to_zero():
    """CR-01: model returning negative mu must not crash or violate band invariant.

    Builds a minimal 30-day single-product sales frame, mocks model.predict
    to return [-1.0], and asserts that:
      - predicted_demand >= 0 (not the raw negative output)
      - demand_lower <= predicted_demand (band invariant holds)
    """
    # Minimal sales DataFrame: 30 days, one product, one merchant.
    dates = pd.date_range(end="2026-04-13", periods=30, freq="D")
    rows = [
        {"date": d, "merchant_id": "mock_merchant", "product": "tomato", "quantity": 10.0}
        for d in dates
    ]
    sales = pd.DataFrame(rows)

    # Mock model that always returns a negative prediction.
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([-1.0])

    # We need a feature_cols list that matches what the feature pipeline produces.
    # Build it by running the pipeline once and capturing column names.
    from meshek_ml.forecasting.features import (
        add_calendar_features,
        add_lag_features,
        add_rolling_features,
    )

    df = sales.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["merchant_id", "product", "date"]).reset_index(drop=True)
    df = add_lag_features(df, target_col="quantity")
    df = add_rolling_features(df, target_col="quantity")
    df = add_calendar_features(df)
    feature_cols = [
        c for c in df.columns
        if c not in ("date", "merchant_id", "product", "quantity")
    ]

    resp = tier_3_ml_forecast(
        merchant_id="mock_merchant",
        sales=sales,
        model=mock_model,
        residual_std=1.0,
        feature_cols=feature_cols,
    )

    rec = resp.recommendations[0]
    assert rec.predicted_demand >= 0, (
        f"predicted_demand must be >= 0, got {rec.predicted_demand}"
    )
    assert rec.demand_lower <= rec.predicted_demand, (
        f"band invariant violated: demand_lower={rec.demand_lower} > "
        f"predicted_demand={rec.predicted_demand}"
    )


@pytest.mark.integration
def test_inference_never_reads_disk(
    trained_model_bundle, merchant_store_factory, monkeypatch
):
    from meshek_ml.recommendation import model_io

    def boom(*a, **kw):
        raise AssertionError(
            "load_model_bundle must not be called at inference time"
        )

    monkeypatch.setattr(model_io, "load_model_bundle", boom)
    merchant_store_factory("tier3e", days=30)
    with MerchantStore("tier3e", must_exist=True) as store:
        sales = store.read_sales()
    for _ in range(5):
        resp = tier_3_ml_forecast(
            merchant_id="tier3e",
            sales=sales,
            model=trained_model_bundle["model"],
            residual_std=trained_model_bundle["residual_std"],
            feature_cols=trained_model_bundle["feature_cols"],
        )
        assert resp.recommendations[0].reasoning_tier == "ml_forecast"
