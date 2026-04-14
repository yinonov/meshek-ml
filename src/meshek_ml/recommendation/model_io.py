"""Safe persistence helpers for LightGBM recommendation model bundles.

Security notes:
  - joblib is the scikit-learn recommended persistence format for
    trained estimators. Bundles MUST only be written and read by the
    service itself (never uploaded by users). Plan 04's lifespan hook
    loads from MESHEK_MODEL_PATH, a deploy-env variable that is never
    caller-controlled.
  - load_model_bundle / save_model_bundle reject paths that resolve
    outside the configured models root to defend against path traversal
    via a poisoned MESHEK_MODEL_PATH value (T-6-08).
  - The loader validates that required keys are present so corrupted or
    foreign files fail loudly rather than returning junk (T-6-09).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypedDict

import joblib


class ModelBundle(TypedDict):
    model: Any
    residual_std: float
    feature_cols: list[str]


_REQUIRED_KEYS = ("model", "residual_std", "feature_cols")

DEFAULT_MODELS_DIR = Path("models").resolve()


def _models_root() -> Path:
    """Resolve the allowed models root.

    Priority: MESHEK_MODELS_DIR env var (if set) > DEFAULT_MODELS_DIR.
    Read on every call so tests that monkeypatch the env var see updates.
    """
    raw = os.environ.get("MESHEK_MODELS_DIR")
    if raw:
        return Path(raw).resolve()
    return DEFAULT_MODELS_DIR


def _assert_within_root(path: Path) -> Path:
    """Resolve ``path`` and confirm it lives inside the allowed root."""
    resolved = Path(path).resolve()
    root = _models_root()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Model path {resolved} is outside the allowed models root {root}"
        ) from exc
    return resolved


def save_model_bundle(bundle: ModelBundle, path: Path) -> Path:
    """Persist ``bundle`` to ``path`` via joblib, within the allowed root."""
    resolved = _assert_within_root(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, resolved)
    return resolved


def load_model_bundle(path: Path) -> ModelBundle:
    """Load a ``ModelBundle`` from disk, enforcing the traversal guard."""
    resolved = _assert_within_root(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Model bundle not found at {resolved}")
    obj = joblib.load(resolved)
    if not isinstance(obj, dict):
        raise ValueError(f"Model file {resolved} is not a ModelBundle dict")
    missing = [k for k in _REQUIRED_KEYS if k not in obj]
    if missing:
        raise ValueError(
            f"Model bundle at {resolved} is missing required keys: {missing}"
        )
    return obj  # type: ignore[return-value]
