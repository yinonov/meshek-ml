"""Tests for POST /recommend — all three tiers + degraded-mode coverage.

Plan 08-04, API-04, REC-04.

Tier routing thresholds (inherited from engine.py D-01):
    - n_days == 0         -> "category_default" (Tier 1)
    - 1 <= n_days < 14    -> "pooled_prior"     (Tier 2)
    - n_days >= 14        -> "ml_forecast"      (Tier 3, requires model)
"""
from __future__ import annotations

import pandas as pd
import pytest

from meshek_ml.storage import MerchantProfile, MerchantStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_merchant(data_dir, merchant_id: str, days: int) -> None:
    """Create a merchant store with ``days`` distinct sale dates.

    Mirrors the pattern from tests/recommendation/conftest.py::merchant_store_factory.
    MESHEK_DATA_DIR is already patched by the ``data_dir`` fixture.
    """
    with MerchantStore(merchant_id) as store:
        store.create_profile(MerchantProfile(merchant_id=merchant_id))
        if days <= 0:
            return
        dates = pd.date_range(end="2026-04-13", periods=days, freq="D")
        rows = []
        for d in dates:
            for product in ["tomato", "cucumber", "onion"]:
                rows.append(
                    {
                        "date": d,
                        "merchant_id": merchant_id,
                        "product": product,
                        "quantity": 10.0,
                    }
                )
        store.write_sales(pd.DataFrame(rows))


# ---------------------------------------------------------------------------
# Tier 1/2/3 happy-path tests (app_client — model loaded)
# ---------------------------------------------------------------------------


def test_recommend_tier1(app_client, data_dir):
    """Tier 1: zero sales → reasoning_tier == 'category_default'."""
    _seed_merchant(data_dir, "rec_t1", days=0)
    resp = app_client.post("/recommend", json={"merchant_id": "rec_t1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reasoning_tier"] == "category_default"
    assert body["merchant_id"] == "rec_t1"
    assert "confidence_score" in body
    assert "recommendations" in body


def test_recommend_tier2(app_client, data_dir):
    """Tier 2: 3 days of sales → reasoning_tier == 'pooled_prior'."""
    # Seed two filler merchants with 14+ days so pooled prior is populated.
    _seed_merchant(data_dir, "filler_a", days=14)
    _seed_merchant(data_dir, "filler_b", days=14)
    _seed_merchant(data_dir, "rec_t2", days=3)
    resp = app_client.post("/recommend", json={"merchant_id": "rec_t2"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reasoning_tier"] == "pooled_prior"
    assert 0.3 <= body["confidence_score"] <= 0.6


def test_recommend_tier3(app_client, data_dir):
    """Tier 3: 20 days of sales + model loaded → reasoning_tier == 'ml_forecast'."""
    _seed_merchant(data_dir, "rec_t3", days=20)
    resp = app_client.post("/recommend", json={"merchant_id": "rec_t3"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reasoning_tier"] == "ml_forecast"
    assert 0.6 <= body["confidence_score"] <= 0.95


def test_engine_is_cached_on_app_state(app_client):
    """app.state.engine is set and not None after lifespan enters."""
    engine = app_client.app.state.engine
    assert engine is not None


def test_catalog_on_app_state(app_client):
    """app.state.catalog is populated and not None after lifespan enters."""
    catalog = app_client.app.state.catalog
    assert catalog is not None


# ---------------------------------------------------------------------------
# Invalid request
# ---------------------------------------------------------------------------


def test_recommend_invalid_merchant_id(app_client):
    """merchant_id with path-traversal chars is rejected 422 at the edge (T-5-01)."""
    resp = app_client.post("/recommend", json={"merchant_id": "../../../etc/passwd"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Degraded-mode tests (no_model_client — model file missing)
# ---------------------------------------------------------------------------


def test_missing_model(no_model_client, data_dir):
    """Tier 3 without a loaded model → 503 with envelope (plan 05 tightened)."""
    _seed_merchant(data_dir, "deg_t3", days=20)
    resp = no_model_client.post("/recommend", json={"merchant_id": "deg_t3"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "model_unavailable"


def test_tier1_in_degraded_mode(no_model_client, data_dir):
    """Tier 1 still returns 200 when the model is absent (model not needed)."""
    _seed_merchant(data_dir, "deg_t1", days=0)
    resp = no_model_client.post("/recommend", json={"merchant_id": "deg_t1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reasoning_tier"] == "category_default"


def test_sales_uses_app_state_catalog(app_client, data_dir):
    """sales.py reads catalog from app.state.catalog (not lru_cache).

    Indirectly verified: if routes/sales.py still uses _get_catalog() the
    lru_cache import would survive; this test checks the route works end-to-end
    using the lifespan-populated catalog (i.e. the free-text parse path still
    functions after migration).
    """
    _seed_merchant(data_dir, "cat_test", days=0)
    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "cat_test",
            "date": "2026-04-13",
            "text": "20 עגבניות",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted_rows"] >= 1
