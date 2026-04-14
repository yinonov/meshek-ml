"""Pydantic schemas for the recommendation service (D-13, D-14).

These are the locked response contracts that Phase 6 Waves 2-4 and
Phase 8's HTTP layer import against. Do not widen the ``reasoning_tier``
literal or the ``confidence_score`` bounds without a context update.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]


class ProductRecommendation(BaseModel):
    """A single per-product order recommendation (D-14)."""

    product_id: str
    quantity: float
    unit: str


class RecommendationResponse(BaseModel):
    """Full response envelope for one merchant order recommendation (D-13)."""

    merchant_id: str
    recommendations: list[ProductRecommendation]
    reasoning_tier: ReasoningTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    generated_at: datetime
