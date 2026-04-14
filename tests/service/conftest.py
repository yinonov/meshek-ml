"""Shared fixtures for Phase 6 service-layer tests."""
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
