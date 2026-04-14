"""Integration tests for ``build_lifespan`` (INFRA-01)."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from meshek_ml.service import lifespan as lifespan_mod
from meshek_ml.service.lifespan import DEFAULT_MODEL_PATH, build_lifespan


@pytest.mark.integration
def test_loads_on_startup(model_bundle_path):
    app = FastAPI(lifespan=build_lifespan(model_path=model_bundle_path))
    with TestClient(app) as client:
        assert client is not None
        state = app.state.ml
        assert state is not None
        assert state.model is not None
        assert state.residual_std >= 0.0
        assert isinstance(state.feature_cols, list)
        assert len(state.feature_cols) > 0
        assert state.model_path == model_bundle_path


@pytest.mark.integration
def test_missing_model_file(tmp_path):
    missing = tmp_path / "nope.bundle"
    app = FastAPI(lifespan=build_lifespan(model_path=missing))
    with pytest.raises(RuntimeError, match="Model file not found"):
        with TestClient(app):
            pass


@pytest.mark.integration
def test_env_var_fallback(model_bundle_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODEL_PATH", str(model_bundle_path))
    app = FastAPI(lifespan=build_lifespan())
    with TestClient(app):
        state = app.state.ml
        assert state is not None
        assert state.model_path == model_bundle_path


def test_default_path_when_no_env(monkeypatch):
    monkeypatch.delenv("MESHEK_MODEL_PATH", raising=False)
    # We only check the resolver, not startup (no file exists at default).
    from meshek_ml.service.lifespan import _resolve_model_path

    assert _resolve_model_path(None) == DEFAULT_MODEL_PATH


@pytest.mark.integration
def test_loader_called_once(model_bundle_path, monkeypatch):
    counter = {"n": 0}
    real_loader = lifespan_mod.load_model_bundle

    def counting_loader(p: Path):
        counter["n"] += 1
        return real_loader(p)

    monkeypatch.setattr(lifespan_mod, "load_model_bundle", counting_loader)
    app = FastAPI(lifespan=build_lifespan(model_path=model_bundle_path))

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app) as client:
        for _ in range(5):
            assert client.get("/ping").status_code == 200
        assert app.state.ml is not None
    assert counter["n"] == 1, f"Expected 1 load call, got {counter['n']}"
    assert app.state.ml is None  # teardown cleared state


@pytest.mark.integration
def test_teardown_clears_state(model_bundle_path):
    app = FastAPI(lifespan=build_lifespan(model_path=model_bundle_path))
    with TestClient(app):
        assert app.state.ml is not None
    assert app.state.ml is None
