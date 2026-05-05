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
from typing import Any

import pandas as pd

from meshek_ml.forecasting.features import (
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
)
from meshek_ml.recommendation.config import CategoryDefaultsConfig
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.recommendation.schema import (
    ProductRecommendation,
    RecommendationResponse,
    Signal,
)


def tier_1_category_defaults(
    merchant_id: str,
    cfg: CategoryDefaultsConfig,
) -> RecommendationResponse:
    """Return category default quantities for a 0-day merchant (D-04)."""
    recs = [
        ProductRecommendation(
            product_id=p.product_id,
            unit=p.unit,
            predicted_demand=p.default_quantity,
            demand_lower=p.default_quantity,   # placeholder; Phase 14 fills with variance
            demand_upper=p.default_quantity,   # placeholder
            reasoning_tier="category_default",
            confidence_score=0.2,
            signals=[Signal(
                name="category_default",
                contribution=1.0,
                copy_key="signal.tier_1_default",
            )],
        )
        for p in cfg.products
    ]
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
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
    # D-06: linear 0.3 → 0.6 across n_days ∈ [1, 13] — computed before loop (Pitfall 8)
    confidence = 0.3 + (0.6 - 0.3) * ((max(1, n_days) - 1) / 12)
    recs: list[ProductRecommendation] = []
    for product, pooled_mean in pooled_means.items():
        own_mean = own_means.get(product, pooled_mean)
        q = shrink * own_mean + (1 - shrink) * pooled_mean
        recs.append(
            ProductRecommendation(
                product_id=product,
                unit="kg",
                predicted_demand=round(q, 4),
                demand_lower=round(q, 4),   # placeholder
                demand_upper=round(q, 4),   # placeholder
                reasoning_tier="pooled_prior",
                confidence_score=round(confidence, 6),
                signals=[Signal(
                    name="pooled_prior",
                    contribution=1.0,
                    copy_key="signal.tier_2_default",
                )],
            )
        )
    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        generated_at=datetime.now(timezone.utc),
    )


def tier_3_ml_forecast(
    merchant_id: str,
    sales: pd.DataFrame,
    model: Any,
    residual_std: float,
    feature_cols: list[str],
    underage_cost: float = 2.0,
    overage_cost: float = 1.0,
) -> RecommendationResponse:
    """LightGBM-forecasted per-product order recommendation (REC-03).

    Reuses ``forecasting.features.*`` to produce an inference feature
    row identical in shape to the training-time feature matrix. Exposes
    the forecasted mean demand as ``predicted_demand`` directly (WIRE-05:
    newsvendor layer removed from response path). Demand band derived from
    +-1 sigma residual_std.

    Inference is stateless: the caller supplies an already-loaded model
    bundle (Plan 04's lifespan hook). This function never touches disk
    and never re-loads the bundle from the filesystem — enforced by
    ``test_inference_never_reads_disk`` (INFRA-01).
    """
    if sales.empty:
        raise ValueError("tier_3_ml_forecast requires non-empty sales history")

    df = sales.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["merchant_id", "product", "date"]).reset_index(drop=True)
    df = add_lag_features(df, target_col="quantity")
    df = add_rolling_features(df, target_col="quantity")
    df = add_calendar_features(df)

    # One latest-date row per product = the inference feature matrix.
    last_rows = (
        df.sort_values("date").groupby("product", as_index=False).tail(1)
    )
    # Pitfall 1: impute NaN features (lag/rolling warmup) with column mean.
    x = last_rows.reindex(columns=feature_cols)
    means = x.mean(numeric_only=True)
    x = x.fillna(means).fillna(0.0)

    mu = model.predict(x)

    # Pitfall 2: residual-std-based confidence is a placeholder. Higher
    # relative residual_std => lower confidence. Clipped to [0.6, 0.95].
    # Must be computed BEFORE the per-product loop (Pitfall 8).
    y_mean = float(sales["quantity"].mean()) or 1.0
    raw = 1.0 - (float(residual_std) / y_mean)
    confidence = max(0.6, min(0.95, raw))

    recs: list[ProductRecommendation] = []
    for product, mean_demand in zip(last_rows["product"], mu, strict=False):
        mu_f = float(mean_demand)
        recs.append(
            ProductRecommendation(
                product_id=str(product),
                unit="kg",
                predicted_demand=round(mu_f, 4),
                demand_lower=round(max(0.0, mu_f - float(residual_std)), 4),
                demand_upper=round(mu_f + float(residual_std), 4),
                reasoning_tier="ml_forecast",
                confidence_score=round(confidence, 6),
                signals=[Signal(
                    name="ml_forecast",
                    contribution=1.0,
                    copy_key="signal.tier_3_default",
                )],
            )
        )

    return RecommendationResponse(
        merchant_id=merchant_id,
        recommendations=recs,
        generated_at=datetime.now(timezone.utc),
    )
