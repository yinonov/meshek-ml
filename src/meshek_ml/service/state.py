"""Service-layer shared state loaded at FastAPI startup."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AppState:
    """Holds the LightGBM model and its training-time metadata.

    Populated once by the lifespan hook (Plan 04) and read per-request
    by RecommendationEngine Tier 3. Never mutated after startup.
    """
    model: Any
    model_path: Path
    residual_std: float
    feature_cols: list[str] = field(default_factory=list)
