"""RecommendationEngine façade + tier router (Phase 6 Plan 04).

Routes every ``recommend(merchant_id)`` call to Tier 1, Tier 2, or Tier 3
based on the merchant's own-history depth measured as
``sales["date"].nunique()``. Branches on ``.empty`` FIRST (Pitfall 4)
before computing ``nunique`` so zero-row DataFrames never raise.

Thresholds (D-01):
    - ``n_days == 0``        -> Tier 1 (category defaults)
    - ``1 <= n_days < 14``   -> Tier 2 (pooled priors)
    - ``n_days >= 14``       -> Tier 3 (LightGBM forecast)

Tier 3 requires a pre-loaded model bundle (the Plan 04 lifespan hook
populates ``app.state.ml`` at FastAPI startup, INFRA-01). The engine
itself never touches disk for model loading.
"""
from __future__ import annotations

from typing import Any, Callable

from meshek_ml.recommendation.config import CategoryDefaultsConfig
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.recommendation.schema import RecommendationResponse
from meshek_ml.recommendation.tiers import (
    tier_1_category_defaults,
    tier_2_pooled_priors,
    tier_3_ml_forecast,
)
from meshek_ml.storage import MerchantStore


class RecommendationEngine:
    """Stateless façade that routes a merchant to one of three tiers."""

    TIER_3_MIN_DAYS: int = 14  # D-01

    def __init__(
        self,
        *,
        store_factory: Callable[[str], MerchantStore],
        pooled_store: PooledStore,
        category_defaults: CategoryDefaultsConfig,
        model: Any = None,
        residual_std: float = 0.0,
        feature_cols: list[str] | None = None,
    ) -> None:
        self._store_factory = store_factory
        self._pooled = pooled_store
        self._category_defaults = category_defaults
        self._model = model
        self._residual_std = residual_std
        self._feature_cols = list(feature_cols or [])

    def recommend(self, merchant_id: str) -> RecommendationResponse:
        """Return a ``RecommendationResponse`` for ``merchant_id``.

        Raises:
            UnknownMerchantError: when the merchant has no store on disk
                (propagated from ``MerchantStore(must_exist=True)``).
            RuntimeError: when Tier 3 is selected but no model bundle
                has been injected.
        """
        with self._store_factory(merchant_id) as store:
            sales = store.read_sales()

        # Pitfall 4: branch on empty FIRST, then compute nunique.
        if sales.empty:
            return tier_1_category_defaults(merchant_id, self._category_defaults)
        n_days = int(sales["date"].nunique())
        if n_days == 0:
            return tier_1_category_defaults(merchant_id, self._category_defaults)
        if n_days < self.TIER_3_MIN_DAYS:
            return tier_2_pooled_priors(
                merchant_id=merchant_id,
                own_sales=sales,
                pooled=self._pooled,
                n_days=n_days,
            )
        if self._model is None:
            raise RuntimeError(
                "Tier 3 requires a loaded model. Ensure lifespan startup "
                "populated app.state.ml before calling recommend()."
            )
        return tier_3_ml_forecast(
            merchant_id=merchant_id,
            sales=sales,
            model=self._model,
            residual_std=self._residual_std,
            feature_cols=self._feature_cols,
        )
