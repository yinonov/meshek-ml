"""Tests for the safe model-bundle persistence helpers (06-03 Task 1)."""
from __future__ import annotations

from pathlib import Path

import joblib
import pytest

from meshek_ml.recommendation.model_io import (
    ModelBundle,
    load_model_bundle,
    save_model_bundle,
)


class _StubModel:
    """Module-level so joblib can serialise it during tests."""

    def predict(self, x):  # pragma: no cover - not exercised here
        return [0.0] * len(x)


def _fake_bundle() -> ModelBundle:
    return {
        "model": _StubModel(),
        "residual_std": 1.5,
        "feature_cols": ["a", "b", "c"],
    }


def test_save_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bundle = _fake_bundle()
    target = tmp_path / "m.bundle"
    save_model_bundle(bundle, target)
    loaded = load_model_bundle(target)
    assert set(loaded.keys()) == {"model", "residual_std", "feature_cols"}
    assert loaded["residual_std"] == 1.5
    assert loaded["feature_cols"] == ["a", "b", "c"]


def test_rejects_path_outside_models_dir(tmp_path, monkeypatch):
    # Allowed root is a subdirectory of tmp_path.
    root = tmp_path / "allowed"
    root.mkdir()
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(root))
    outside = tmp_path / "escape.bundle"
    with pytest.raises(ValueError, match="outside"):
        load_model_bundle(outside)


def test_rejects_missing_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    bad = tmp_path / "bad.bundle"
    joblib.dump({"residual_std": 1.0, "feature_cols": []}, bad)
    with pytest.raises(ValueError, match="model"):
        load_model_bundle(bad)


def test_rejects_nonexistent_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_model_bundle(tmp_path / "nope.bundle")


def test_save_rejects_path_outside_models_dir(tmp_path, monkeypatch):
    root = tmp_path / "allowed"
    root.mkdir()
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(root))
    outside = tmp_path / "escape.bundle"
    with pytest.raises(ValueError, match="outside"):
        save_model_bundle(_fake_bundle(), outside)
