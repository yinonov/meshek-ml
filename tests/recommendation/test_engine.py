"""Unit tests for the RecommendationEngine tier router."""
from __future__ import annotations

import pytest

from meshek_ml.recommendation import RecommendationEngine
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.storage import MerchantStore, UnknownMerchantError


def _make_engine(category_defaults_cfg, bundle=None):
    return RecommendationEngine(
        store_factory=lambda mid: MerchantStore(mid, must_exist=True),
        pooled_store=PooledStore(),
        category_defaults=category_defaults_cfg,
        model=bundle["model"] if bundle else None,
        residual_std=bundle["residual_std"] if bundle else 0.0,
        feature_cols=bundle["feature_cols"] if bundle else None,
    )


def test_tier_1_routing_zero_days(
    data_root, merchant_store_factory, category_defaults_cfg
):
    merchant_store_factory("m_zero", days=0)
    engine = _make_engine(category_defaults_cfg)
    resp = engine.recommend("m_zero")
    assert resp.recommendations[0].reasoning_tier == "category_default"
    assert resp.recommendations[0].confidence_score == 0.2
    assert resp.merchant_id == "m_zero"


def test_tier_2_routing_at_1_day(
    data_root, merchant_store_factory, category_defaults_cfg
):
    # Two filler merchants with 14 days so the pooled prior is populated.
    merchant_store_factory("filler_a", days=14)
    merchant_store_factory("filler_b", days=14)
    merchant_store_factory("m_one", days=1)
    engine = _make_engine(category_defaults_cfg)
    resp = engine.recommend("m_one")
    assert resp.recommendations[0].reasoning_tier == "pooled_prior"
    assert 0.3 <= resp.recommendations[0].confidence_score <= 0.6


def test_tier_2_routing_at_13_days(
    data_root, merchant_store_factory, category_defaults_cfg
):
    merchant_store_factory("filler_a", days=14)
    merchant_store_factory("filler_b", days=14)
    merchant_store_factory("m_thirteen", days=13)
    engine = _make_engine(category_defaults_cfg)
    resp = engine.recommend("m_thirteen")
    assert resp.recommendations[0].reasoning_tier == "pooled_prior"
    assert 0.3 <= resp.recommendations[0].confidence_score <= 0.6


@pytest.mark.integration
def test_tier_3_routing_at_14_days(
    data_root,
    merchant_store_factory,
    category_defaults_cfg,
    trained_model_bundle,
):
    merchant_store_factory("m_14", days=14)
    engine = _make_engine(category_defaults_cfg, bundle=trained_model_bundle)
    resp = engine.recommend("m_14")
    assert resp.recommendations[0].reasoning_tier == "ml_forecast"
    assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95


@pytest.mark.integration
def test_tier_3_routing_at_30_days(
    data_root,
    merchant_store_factory,
    category_defaults_cfg,
    trained_model_bundle,
):
    merchant_store_factory("m_30", days=30)
    engine = _make_engine(category_defaults_cfg, bundle=trained_model_bundle)
    resp = engine.recommend("m_30")
    assert resp.recommendations[0].reasoning_tier == "ml_forecast"
    assert 0.6 <= resp.recommendations[0].confidence_score <= 0.95


@pytest.mark.integration
def test_confidence_bounds_per_tier(
    data_root,
    merchant_store_factory,
    category_defaults_cfg,
    trained_model_bundle,
):
    merchant_store_factory("filler_a", days=14)
    merchant_store_factory("filler_b", days=14)
    merchant_store_factory("t1", days=0)
    merchant_store_factory("t2", days=7)
    merchant_store_factory("t3", days=30)
    engine = _make_engine(category_defaults_cfg, bundle=trained_model_bundle)
    assert engine.recommend("t1").recommendations[0].confidence_score == 0.2
    r2 = engine.recommend("t2")
    assert 0.3 <= r2.recommendations[0].confidence_score <= 0.6
    r3 = engine.recommend("t3")
    assert 0.6 <= r3.recommendations[0].confidence_score <= 0.95


def test_unknown_merchant_raises(data_root, category_defaults_cfg):
    engine = _make_engine(category_defaults_cfg)
    with pytest.raises(UnknownMerchantError):
        engine.recommend("ghost")


def test_response_contract_rec04(
    data_root, merchant_store_factory, category_defaults_cfg
):
    merchant_store_factory("filler_a", days=14)
    merchant_store_factory("filler_b", days=14)
    merchant_store_factory("m_zero", days=0)
    merchant_store_factory("m_seven", days=7)
    engine = _make_engine(category_defaults_cfg)
    for mid in ("m_zero", "m_seven"):
        resp = engine.recommend(mid)
        assert resp.recommendations[0].reasoning_tier is not None
        assert resp.recommendations[0].confidence_score is not None
