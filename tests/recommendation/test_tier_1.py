"""Tests for tier_1_category_defaults (D-03/D-04)."""
from __future__ import annotations

from meshek_ml.recommendation.tiers import tier_1_category_defaults


def test_returns_category_default_tier(category_defaults_cfg):
    resp = tier_1_category_defaults("shop_a", category_defaults_cfg)
    assert resp.reasoning_tier == "category_default"


def test_confidence_is_0_2(category_defaults_cfg):
    resp = tier_1_category_defaults("shop_a", category_defaults_cfg)
    assert resp.confidence_score == 0.2


def test_quantities_match_yaml(category_defaults_cfg):
    resp = tier_1_category_defaults("shop_a", category_defaults_cfg)
    by_id = {r.product_id: r for r in resp.recommendations}
    for p in category_defaults_cfg.products:
        rec = by_id[p.product_id]
        assert rec.quantity == p.default_quantity
        assert rec.unit == p.unit


def test_merchant_id_propagated(category_defaults_cfg):
    resp = tier_1_category_defaults("shop_xyz", category_defaults_cfg)
    assert resp.merchant_id == "shop_xyz"
