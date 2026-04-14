"""FastAPI lifespan factory — loads LightGBM model once at startup.

Implements INFRA-01 / D-10 / D-11 / D-12. Phase 8 will pass the
returned factory to ``FastAPI(lifespan=...)``; Phase 6 only ships the
factory and verifies it with a bare ``FastAPI()`` smoke test.

Security notes:
    - ``MESHEK_MODEL_PATH`` is a deploy-operator-controlled environment
      variable, read once at process startup and never from a request
      (T-6-12). The underlying ``load_model_bundle`` additionally
      enforces a ``relative_to(MESHEK_MODELS_DIR)`` traversal guard.
    - State is attached to ``app.state.ml`` — never a module-level
      global — so tests cannot leak across each other (Pitfall 3,
      T-6-14).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Callable

from fastapi import FastAPI

from meshek_ml.recommendation.model_io import load_model_bundle
from meshek_ml.service.state import AppState

DEFAULT_MODEL_PATH = Path("models/lightgbm_v1.bundle")


def _resolve_model_path(explicit: Path | None) -> Path:
    """Resolve the effective model path.

    Priority: explicit arg > ``MESHEK_MODEL_PATH`` env > ``DEFAULT_MODEL_PATH``.
    """
    if explicit is not None:
        return explicit
    env = os.environ.get("MESHEK_MODEL_PATH")
    if env:
        return Path(env)
    return DEFAULT_MODEL_PATH


def build_lifespan(model_path: Path | None = None) -> Callable:
    """Return an ``@asynccontextmanager`` bound to a specific model path.

    The resolved path is fixed at factory-call time (not at startup) so
    the env var is read exactly once when the factory is invoked. The
    returned context manager fails fast at enter if the file does not
    exist, populates ``app.state.ml`` with an ``AppState`` on startup,
    and clears it on shutdown.
    """
    resolved = _resolve_model_path(model_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not resolved.exists():
            raise RuntimeError(
                f"Model file not found at {resolved}. "
                f"Set MESHEK_MODEL_PATH or train a model first via "
                f"meshek_ml.recommendation.training.train_and_save()."
            )
        bundle = load_model_bundle(resolved)
        app.state.ml = AppState(
            model=bundle["model"],
            model_path=resolved,
            residual_std=bundle["residual_std"],
            feature_cols=bundle["feature_cols"],
        )
        try:
            yield
        finally:
            app.state.ml = None

    return lifespan
