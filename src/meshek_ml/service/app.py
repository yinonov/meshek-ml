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
- Plan 04 will extend ``_build_engine_lifespan`` to also populate
  ``app.state.engine`` and ``app.state.catalog``; keep this wrapper
  minimal so that extension is clean.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from meshek_ml.service.lifespan import build_lifespan
from meshek_ml.service.routes import health, merchants, sales
from meshek_ml.service.schemas import SERVICE_VERSION

logger = logging.getLogger(__name__)


def _build_engine_lifespan():
    """Return an asynccontextmanager that wraps Phase 6 lifespan with degraded-start.

    Degraded-start contract (research §Testing Strategy):
    If ``build_lifespan()`` raises ``RuntimeError`` at enter (model file
    missing), we catch it, log a warning with ``exc_info=True`` (server-side
    only — T-8-03), set ``app.state.ml = None``, and yield.  The service
    boots in degraded mode; ``GET /health`` returns 503.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        phase6_lifespan = build_lifespan()
        try:
            async with phase6_lifespan(app):
                yield
        except RuntimeError as exc:
            logger.warning(
                "model load failed: %s — starting in degraded mode",
                exc,
                exc_info=True,
            )
            app.state.ml = None
            yield

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
    return app
