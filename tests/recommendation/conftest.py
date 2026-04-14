"""Shared fixtures for Phase 6 recommendation tests."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
import pytest

from meshek_ml.recommendation.config import (
    CategoryDefaultsConfig,
    load_category_defaults,
)
from meshek_ml.storage import MerchantProfile, MerchantStore


@pytest.fixture
def data_root(tmp_path, monkeypatch) -> Path:
    """Isolate MESHEK_DATA_DIR to a per-test tmp_path (D-02)."""
    root = tmp_path / "merchants"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MESHEK_DATA_DIR", str(root))
    return root


@pytest.fixture
def merchant_store_factory(
    data_root,
) -> Callable[[str, int, Optional[list[str]], float], None]:
    """Factory for creating a populated MerchantStore with `days` distinct dates."""

    def _factory(
        merchant_id: str,
        days: int,
        products: Optional[list[str]] = None,
        qty: float = 10.0,
    ) -> None:
        products = products or ["tomato", "cucumber", "onion"]
        with MerchantStore(merchant_id) as store:
            store.create_profile(MerchantProfile(merchant_id=merchant_id))
            if days <= 0:
                return
            dates = pd.date_range(end="2026-04-13", periods=days, freq="D")
            rows = []
            for d in dates:
                for p in products:
                    rows.append(
                        {
                            "date": d,
                            "merchant_id": merchant_id,
                            "product": p,
                            "quantity": qty,
                        }
                    )
            df = pd.DataFrame(rows)
            store.write_sales(df)

    return _factory


@pytest.fixture
def category_defaults_cfg() -> CategoryDefaultsConfig:
    return load_category_defaults(
        Path("configs/recommendation/category_defaults.yaml")
    )


@pytest.fixture(scope="session")
def trained_model_bundle(tmp_path_factory):
    """Session-scoped Tier 3 LightGBM bundle trained on synthetic data.

    Sets MESHEK_MODELS_DIR manually (session scope cannot use the
    function-scoped ``monkeypatch`` fixture) and restores any prior value
    on teardown.
    """
    from meshek_ml.recommendation.training import train_and_save
    from meshek_ml.simulation.generator import run_simulation

    root = tmp_path_factory.mktemp("models-session")
    prev = os.environ.get("MESHEK_MODELS_DIR")
    os.environ["MESHEK_MODELS_DIR"] = str(root)
    try:
        data = run_simulation(
            n_merchants=3,
            start_date="2024-01-01",
            end_date="2024-03-31",
            seed=42,
        )
        bundle = train_and_save(root / "tier3.bundle", data)
        yield bundle
    finally:
        if prev is None:
            os.environ.pop("MESHEK_MODELS_DIR", None)
        else:
            os.environ["MESHEK_MODELS_DIR"] = prev
