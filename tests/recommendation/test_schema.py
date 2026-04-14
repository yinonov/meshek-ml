"""Tests for meshek_ml.recommendation.schema (Phase 6 Plan 01)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
)


def _valid_response_kwargs(**overrides):
    base = dict(
        merchant_id="shop_a",
        recommendations=[
            ProductRecommendation(product_id="tomato", quantity=8.0, unit="kg"),
        ],
        reasoning_tier="category_default",
        confidence_score=0.2,
        generated_at=datetime.now(timezone.utc),
    )
    base.update(overrides)
    return base


def test_required_fields():
    """reasoning_tier is required."""
    kwargs = _valid_response_kwargs()
    kwargs.pop("reasoning_tier")
    with pytest.raises(ValidationError):
        RecommendationResponse(**kwargs)


def test_reasoning_tier_literal():
    """reasoning_tier must be one of the three literal values."""
    with pytest.raises(ValidationError):
        RecommendationResponse(**_valid_response_kwargs(reasoning_tier="bogus"))

    for tier in ("category_default", "pooled_prior", "ml_forecast"):
        resp = RecommendationResponse(**_valid_response_kwargs(reasoning_tier=tier))
        assert resp.reasoning_tier == tier


def test_confidence_bounds():
    """confidence_score must be within [0.0, 1.0]."""
    for bad in (-0.1, 1.1):
        with pytest.raises(ValidationError):
            RecommendationResponse(**_valid_response_kwargs(confidence_score=bad))

    for good in (0.0, 0.2, 0.95, 1.0):
        resp = RecommendationResponse(**_valid_response_kwargs(confidence_score=good))
        assert resp.confidence_score == good


def test_product_recommendation_fields():
    """ProductRecommendation requires product_id, quantity, unit."""
    pr = ProductRecommendation(product_id="tomato", quantity=8.0, unit="kg")
    assert pr.product_id == "tomato"
    assert pr.quantity == 8.0
    assert pr.unit == "kg"

    for missing in ("product_id", "quantity", "unit"):
        kwargs = {"product_id": "tomato", "quantity": 8.0, "unit": "kg"}
        kwargs.pop(missing)
        with pytest.raises(ValidationError):
            ProductRecommendation(**kwargs)
