"""Shared fixtures for Phase 6 and Phase 8 service-layer tests."""
from __future__ import annotations

import os

import pytest

from meshek_ml.recommendation.training import train_and_save
from meshek_ml.simulation.generator import run_simulation


@pytest.fixture(scope="session")
def model_bundle_path(tmp_path_factory):
    """Session-scoped fixture: train a real LightGBM bundle on disk.

    Sets ``MESHEK_MODELS_DIR`` to the tmp root for the whole session so
    ``load_model_bundle`` / ``save_model_bundle`` traversal guards accept
    the path. Restores any prior env value on teardown.
    """
    root = tmp_path_factory.mktemp("service-models")
    prev = os.environ.get("MESHEK_MODELS_DIR")
    os.environ["MESHEK_MODELS_DIR"] = str(root)
    try:
        data = run_simulation(
            n_merchants=3,
            start_date="2024-01-01",
            end_date="2024-03-31",
            seed=42,
        )
        bundle_path = root / "lifespan.bundle"
        train_and_save(bundle_path, data)
        yield bundle_path
    finally:
        if prev is None:
            os.environ.pop("MESHEK_MODELS_DIR", None)
        else:
            os.environ["MESHEK_MODELS_DIR"] = prev


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """Function-scoped fixture: creates a merchants subdirectory under tmp_path.

    Sets ``MESHEK_DATA_DIR`` env var so MerchantStore picks it up.
    Returns the path to the data root.
    """
    merchants_dir = tmp_path / "merchants"
    merchants_dir.mkdir()
    monkeypatch.setenv("MESHEK_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def app_client(model_bundle_path, data_dir, monkeypatch):
    """Function-scoped fixture: TestClient backed by a fully-loaded app.

    Sets MESHEK_MODEL_PATH and MESHEK_MODELS_DIR to point at the
    session-scoped trained model bundle so the lifespan loads successfully.
    Yields a ``starlette.testclient.TestClient`` with lifespan fired.
    Import of create_app is deferred inside the fixture so pytest --collect-only
    works before app.py exists.
    """
    from starlette.testclient import TestClient

    monkeypatch.setenv("MESHEK_MODEL_PATH", str(model_bundle_path))
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(model_bundle_path.parent))

    from meshek_ml.service.app import create_app  # deferred import

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


@pytest.fixture()
def no_model_client(data_dir, monkeypatch, tmp_path):
    """Function-scoped fixture: TestClient in degraded mode (model file missing).

    Sets MESHEK_MODEL_PATH to a non-existent path so the lifespan raises
    RuntimeError and create_app() falls back to app.state.ml = None.
    Yields a ``starlette.testclient.TestClient`` with lifespan fired.
    """
    from starlette.testclient import TestClient

    missing_path = tmp_path / "nonexistent.bundle"
    monkeypatch.setenv("MESHEK_MODEL_PATH", str(missing_path))
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))

    from meshek_ml.service.app import create_app  # deferred import

    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client
