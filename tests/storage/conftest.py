"""Shared fixtures for storage layer tests (Phase 5)."""
from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """Isolate MESHEK_DATA_DIR to a per-test tmp_path (D-02)."""
    root = tmp_path / "merchants"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("MESHEK_DATA_DIR", str(root))
    return root


@pytest.fixture
def sample_sales_df():
    """Canonical 3-row sales DataFrame for merchant 'shop_a'."""
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-10", "2026-04-10", "2026-04-11"]),
            "merchant_id": ["shop_a", "shop_a", "shop_a"],
            "product": ["tomato", "cucumber", "tomato"],
            "quantity": [12.5, 8.0, 14.0],
        }
    )
