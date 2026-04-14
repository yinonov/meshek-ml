"""Recommendation engine package (Phase 6)."""
from __future__ import annotations

from meshek_ml.recommendation.engine import RecommendationEngine
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
)

__all__ = [
    "ProductRecommendation",
    "RecommendationEngine",
    "RecommendationResponse",
]
