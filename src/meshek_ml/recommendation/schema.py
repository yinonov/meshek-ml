"""Pydantic schemas for the recommendation service (Phase 12 wire contract).

The locked v1.2 response contract: per-line ``reasoning_tier``,
per-line ``confidence_score``, demand point estimate + band, and
``signals[]`` for explanation. ``quantity`` removed (WIRE-01/WIRE-05).
Phase 14 will tighten ``Signal.name`` to a Literal once the enum locks.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]


class Signal(BaseModel):
    """A single explanation signal for a recommendation line (WIRE-04).

    ``name`` is an open string in v1.2; Phase 14 tightens it to a Literal.
    Documented stable values today: ``"category_default"``, ``"pooled_prior"``,
    ``"ml_forecast"``. ``contribution`` is signed and in raw demand units
    (kg) — same scale as ``predicted_demand``. ``copy_key`` follows the
    ``"signal.<snake_case_name>"`` convention; meshek owns translation.
    """

    name: str
    contribution: float
    copy_key: str


class ProductRecommendation(BaseModel):
    """A single per-product recommendation line (WIRE-01..WIRE-04).

    ``demand_lower <= predicted_demand <= demand_upper`` is enforced via
    ``model_validator(mode="after")``. The placeholder case lower==upper==
    predicted satisfies the invariant trivially (Phase 14 fills variance).
    """

    product_id: str
    unit: str
    predicted_demand: float
    demand_lower: float
    demand_upper: float
    reasoning_tier: ReasoningTier
    confidence_score: float = Field(ge=0.0, le=1.0)
    signals: list[Signal] = Field(min_length=1)

    @model_validator(mode="after")
    def band_contains_estimate(self) -> "ProductRecommendation":
        """Ensure demand_lower <= predicted_demand <= demand_upper (WIRE-01)."""
        if not (self.demand_lower <= self.predicted_demand <= self.demand_upper):
            raise ValueError(
                "demand_lower <= predicted_demand <= demand_upper required"
            )
        return self


class RecommendationResponse(BaseModel):
    """Full response envelope for one merchant recommendation (WIRE-06).

    Note: response-level ``reasoning_tier`` and ``confidence_score`` are
    intentionally absent — they are now per-line on
    ``ProductRecommendation`` (WIRE-02/WIRE-03).
    """

    merchant_id: str
    recommendations: list[ProductRecommendation]
    generated_at: datetime
