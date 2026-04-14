"""End-to-end three-tier engine integration test (ROADMAP success 1-5)."""
from __future__ import annotations

import pytest

from meshek_ml.recommendation import RecommendationEngine
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.storage import MerchantStore


@pytest.mark.integration
def test_three_tiers_single_run(
    data_root,
    merchant_store_factory,
    category_defaults_cfg,
    trained_model_bundle,
):
    # Filler merchants so Tier 2 pooled prior has inputs.
    merchant_store_factory("filler_a", days=14)
    merchant_store_factory("filler_b", days=14)
    # Target merchants covering all three tiers in a single run.
    merchant_store_factory("m_zero", days=0)
    merchant_store_factory("m_seven", days=7)
    merchant_store_factory("m_thirty", days=30)

    engine = RecommendationEngine(
        store_factory=lambda mid: MerchantStore(mid, must_exist=True),
        pooled_store=PooledStore(),
        category_defaults=category_defaults_cfg,
        model=trained_model_bundle["model"],
        residual_std=trained_model_bundle["residual_std"],
        feature_cols=trained_model_bundle["feature_cols"],
    )

    r1 = engine.recommend("m_zero")
    r2 = engine.recommend("m_seven")
    r3 = engine.recommend("m_thirty")

    assert r1.reasoning_tier == "category_default"
    assert r1.confidence_score == 0.2
    assert r2.reasoning_tier == "pooled_prior"
    assert 0.3 <= r2.confidence_score <= 0.6
    assert r3.reasoning_tier == "ml_forecast"
    assert 0.6 <= r3.confidence_score <= 0.95

    for resp in (r1, r2, r3):
        assert resp.reasoning_tier is not None
        assert resp.confidence_score is not None  # REC-04
