"""Tiered recommendation functions (REC-01, REC-02).

Tier 1 (``tier_1_category_defaults``, D-03/D-04) returns category default
quantities with a fixed confidence of 0.2 for brand-new (0-day) merchants.

Tier 2 (``tier_2_pooled_priors``, D-05/D-06) blends the merchant's own
product means with cross-merchant pooled priors using shrinkage
``n / (n + 14)``. Confidence interpolates linearly from 0.3 at n=1 to 0.6
at n=13 days of own history.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from meshek_ml.recommendation.config import CategoryDefaultsConfig
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
)


def tier_1_category_defaults(
    merchant_id: str,
    cfg: CategoryDefaultsConfig,
) -> RecommendationResponse:
    """Return category default quantities for a 0-day merchant (D-04)."""
    recs = [
        ProductRecommendation(
            product_id=p.product_id,
            quantity=p.default_quantity,
            unit=p.unit,
        )
        for p in cfg.products
    ]
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        reasoning_tier="category_default",
        confidence_score=0.2,
        generated_at=datetime.now(timezone.utc),
    )


def tier_2_pooled_priors(
    merchant_id: str,
    own_sales: pd.DataFrame,
    pooled: PooledStore,
    n_days: int,
) -> RecommendationResponse:
    """Blend own means with pooled priors via ``n / (n + 14)`` shrinkage."""
    pooled_means = pooled.pooled_mean_by_product(
        exclude_merchant_id=merchant_id
    )
    own_means: dict[str, float] = (
        own_sales.groupby("product")["quantity"].mean().to_dict()
        if not own_sales.empty
        else {}
    )
    shrink = n_days / (n_days + 14)  # D-05
    recs: list[ProductRecommendation] = []
    for product, pooled_mean in pooled_means.items():
        own_mean = own_means.get(product, pooled_mean)
        q = shrink * own_mean + (1 - shrink) * pooled_mean
        recs.append(
            ProductRecommendation(
                product_id=product, quantity=round(q, 2), unit="kg"
            )
        )
    # D-06: linear 0.3 → 0.6 across n_days ∈ [1, 13]
    confidence = 0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12)
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        reasoning_tier="pooled_prior",
        confidence_score=round(confidence, 6),
        generated_at=datetime.now(timezone.utc),
    )
