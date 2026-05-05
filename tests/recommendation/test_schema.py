"""Tests for meshek_ml.recommendation.schema (Phase 12 wire-contract)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    Signal,
)


def _valid_product_rec_kwargs(**overrides):
    """Return kwargs that produce a valid ProductRecommendation."""
    base = dict(
        product_id="tomato",
        unit="kg",
        predicted_demand=8.0,
        demand_lower=8.0,
        demand_upper=8.0,
        reasoning_tier="category_default",
        confidence_score=0.2,
        signals=[Signal(name="category_default", contribution=1.0, copy_key="signal.tier_1_default")],
    )
    base.update(overrides)
    return base


def _valid_response_kwargs(**overrides):
    """Return kwargs that produce a valid RecommendationResponse."""
    base = dict(
        merchant_id="shop_a",
        recommendations=[
            ProductRecommendation(**_valid_product_rec_kwargs()),
        ],
        generated_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return base


def test_required_fields():
    """reasoning_tier is required on ProductRecommendation."""
    kwargs = _valid_product_rec_kwargs()
    kwargs.pop("reasoning_tier")
    with pytest.raises(ValidationError):
        ProductRecommendation(**kwargs)


def test_reasoning_tier_literal():
    """reasoning_tier must be one of the three literal values."""
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(reasoning_tier="bogus"))

    for tier in ("category_default", "pooled_prior", "ml_forecast"):
        pr = ProductRecommendation(**_valid_product_rec_kwargs(reasoning_tier=tier))
        assert pr.reasoning_tier == tier


def test_confidence_bounds():
    """confidence_score must be within [0.0, 1.0]."""
    for bad in (-0.1, 1.1):
        with pytest.raises(ValidationError):
            ProductRecommendation(**_valid_product_rec_kwargs(confidence_score=bad))

    for good in (0.0, 0.2, 0.95, 1.0):
        pr = ProductRecommendation(**_valid_product_rec_kwargs(confidence_score=good))
        assert pr.confidence_score == good


def test_product_recommendation_fields():
    """ProductRecommendation requires new per-line fields; band invariant enforced."""
    pr = ProductRecommendation(**_valid_product_rec_kwargs())
    assert pr.product_id == "tomato"
    assert pr.predicted_demand == 8.0
    assert pr.demand_lower == 8.0
    assert pr.demand_upper == 8.0
    assert pr.reasoning_tier == "category_default"
    assert pr.confidence_score == 0.2
    assert len(pr.signals) == 1
    assert pr.signals[0].copy_key == "signal.tier_1_default"

    # Band invariant: lower > predicted must raise
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(demand_lower=9.0, demand_upper=8.0))

    # Signals list must have at least one entry
    with pytest.raises(ValidationError):
        ProductRecommendation(**_valid_product_rec_kwargs(signals=[]))

    # Legacy quantity field must not exist
    pr_dict = pr.model_dump()
    assert "quantity" not in pr_dict

    # Response-level reasoning_tier/confidence_score must be absent
    resp = RecommendationResponse(**_valid_response_kwargs())
    resp_dict = resp.model_dump()
    assert "reasoning_tier" not in resp_dict
    assert "confidence_score" not in resp_dict
