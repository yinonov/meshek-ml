"""Tests for tier_3_ml_forecast (REC-03, INFRA-01)."""
from __future__ import annotations

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
    assert resp.reasoning_tier == "ml_forecast"
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
    assert 0.6 <= resp.confidence_score <= 0.95


@pytest.mark.integration
def test_quantities_non_negative(trained_model_bundle, merchant_store_factory):
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
        assert rec.quantity >= 0


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
        assert resp.reasoning_tier == "ml_forecast"
