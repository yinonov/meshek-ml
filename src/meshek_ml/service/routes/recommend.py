"""POST /recommend handler — routes to the Phase 6 RecommendationEngine.

Plan 08-04, API-04, REC-04, D-09.

The engine is instantiated once at startup (INFRA-01) and cached on
``app.state.engine`` by ``_build_engine_lifespan`` in app.py.  This handler
simply reads the cached engine and calls ``recommend()``.

Error handling:
- ``UnknownMerchantError`` bubbles up — plan 05 maps it to 404.
- ``RuntimeError`` (Tier 3 no-model) bubbles up — plan 05 maps it to 503.
  Until plan 05 lands, tests accept ``status in (500, 503)``.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from meshek_ml.recommendation.schema import RecommendationResponse
from meshek_ml.service.schemas import RecommendRequest

router = APIRouter()


@router.post("/recommend", response_model=RecommendationResponse)
def post_recommend(body: RecommendRequest, request: Request) -> RecommendationResponse:
    """Return a recommendation for the requested merchant.

    Reads ``app.state.engine`` (populated by lifespan) and delegates to
    ``RecommendationEngine.recommend(merchant_id)``.  No try/except here —
    exceptions bubble to plan 05's central handler (D-11).
    """
    engine = request.app.state.engine
    return engine.recommend(body.merchant_id)
