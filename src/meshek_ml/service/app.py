"""FastAPI application factory for meshek-ml service.

Entry point: ``meshek_ml.service.app:create_app``
Uvicorn launch: ``uvicorn meshek_ml.service.app:create_app --factory``

Design notes:
- ``create_app()`` is a *sync* ``def`` — required for ``--factory`` mode (Pitfall 4).
- The inner ``_build_engine_lifespan`` wraps Phase 6's ``build_lifespan()``
  in a degraded-start contract: if the model file is missing the Phase 6
  lifespan raises ``RuntimeError`` at enter; we catch it, log a warning,
  set ``app.state.ml = None``, and yield so the app still serves requests.
  ``GET /health`` then returns 503, making the degraded state externally
  visible to orchestrators (Fly.io / Railway health checks — T-8-02).
- Plan 04 extends ``_build_engine_lifespan`` to also populate
  ``app.state.engine`` and ``app.state.catalog`` so recommend and sales
  routes share a single loaded catalog and engine instance (INFRA-01).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI

from meshek_ml.parsing import DEFAULT_CATALOG_PATH, load_catalog
from meshek_ml.recommendation.config import load_category_defaults
from meshek_ml.recommendation.engine import RecommendationEngine
from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.service.lifespan import build_lifespan
from meshek_ml.service.routes import health, merchants, recommend, sales
from meshek_ml.service.schemas import SERVICE_VERSION
from meshek_ml.storage import MerchantStore

logger = logging.getLogger(__name__)

_CATEGORY_DEFAULTS_PATH = Path("configs/recommendation/category_defaults.yaml")


def _build_engine_lifespan():
    """Return an asynccontextmanager that wraps Phase 6 lifespan with degraded-start.

    Degraded-start contract (research §Testing Strategy):
    If ``build_lifespan()`` raises ``RuntimeError`` at enter (model file
    missing), we catch it, log a warning with ``exc_info=True`` (server-side
    only — T-8-03), set ``app.state.ml = None``, and yield.  The service
    boots in degraded mode; ``GET /health`` returns 503.

    Plan 04 extensions (inside the happy-path ``async with`` block):
    - Load parser catalog and assign to ``app.state.catalog`` so both
      ``routes/sales.py`` and any future consumer share one instance.
    - Build ``RecommendationEngine`` with the loaded model (or ``model=None``
      on the degraded path) and assign to ``app.state.engine``.
    - Tier 1 and Tier 2 work in degraded mode; Tier 3 raises ``RuntimeError``
      which plan 05 maps to 503.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        phase6_lifespan = build_lifespan()

        # Load shared resources that work regardless of model health.
        catalog = load_catalog(DEFAULT_CATALOG_PATH)
        app.state.catalog = catalog
        category_defaults = load_category_defaults(_CATEGORY_DEFAULTS_PATH)
        pooled_store = PooledStore()

        try:
            async with phase6_lifespan(app):
                # Happy path: model loaded, all tiers available.
                ml = app.state.ml
                engine = RecommendationEngine(
                    store_factory=lambda mid: MerchantStore(mid, must_exist=True),
                    pooled_store=pooled_store,
                    category_defaults=category_defaults,
                    model=ml.model,
                    residual_std=ml.residual_std,
                    feature_cols=ml.feature_cols,
                )
                app.state.engine = engine
                try:
                    yield
                finally:
                    app.state.engine = None
                    app.state.catalog = None
        except RuntimeError as exc:
            logger.warning(
                "model load failed: %s — starting in degraded mode",
                exc,
                exc_info=True,
            )
            app.state.ml = None
            # Degraded path: Tier 1 and Tier 2 still work; Tier 3 raises.
            engine = RecommendationEngine(
                store_factory=lambda mid: MerchantStore(mid, must_exist=True),
                pooled_store=pooled_store,
                category_defaults=category_defaults,
                model=None,
                residual_std=0.0,
                feature_cols=[],
            )
            app.state.engine = engine
            try:
                yield
            finally:
                app.state.engine = None
                app.state.catalog = None

    return lifespan


def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application.

    This is the factory consumed by uvicorn ``--factory``.  It is a *sync*
    ``def`` by design (Common Pitfall 4 — async factories are not supported
    by uvicorn's ``--factory`` flag).
    """
    app = FastAPI(
        title="meshek-ml",
        version=SERVICE_VERSION,
        lifespan=_build_engine_lifespan(),
    )
    app.include_router(health.router)
    app.include_router(merchants.router)
    app.include_router(sales.router)
    app.include_router(recommend.router)
    return app
