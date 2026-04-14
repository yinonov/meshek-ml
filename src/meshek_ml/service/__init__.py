"""Service-layer package (Phase 6 scaffolding)."""
from __future__ import annotations

from meshek_ml.service.lifespan import DEFAULT_MODEL_PATH, build_lifespan
from meshek_ml.service.state import AppState

__all__ = ["AppState", "DEFAULT_MODEL_PATH", "build_lifespan"]
