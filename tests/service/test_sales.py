"""Tests for POST /sales — structured items and Hebrew free-text paths.

Plan 08-03: dual-shape handler (D-08), partial-success semantics (D-08).
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Task 8-03-01: structured items path
# ---------------------------------------------------------------------------


def test_structured(app_client):
    """POST with structured items persists rows and returns accepted_rows=2."""
    # Pre-create merchant
    resp = app_client.post("/merchants", json={"merchant_id": "shop_struct"})
    assert resp.status_code == 201

    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_struct",
            "date": "2026-04-14",
            "items": [
                {"product_id": "tomato", "quantity": 20, "unit": "kg"},
                {"product_id": "cucumber", "quantity": 5, "unit": "unit"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted_rows"] == 2
    assert body["skipped"] == []

    # Verify persistence via MerchantStore
    import os

    import pandas as pd

    from meshek_ml.storage.merchant_store import MerchantStore

    with MerchantStore("shop_struct") as store:
        df = store.read_sales()

    assert len(df) == 2
    products = set(df["product"].tolist())
    assert "tomato" in products
    assert "cucumber" in products
    qtys = dict(zip(df["product"], df["quantity"]))
    assert qtys["tomato"] == 20.0
    assert qtys["cucumber"] == 5.0


def test_sales_rejects_both_shapes(app_client):
    """POST with both items AND text → 422."""
    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_both",
            "date": "2026-04-14",
            "items": [{"product_id": "tomato", "quantity": 10, "unit": "kg"}],
            "text": "20 עגבניות",
        },
    )
    assert resp.status_code == 422


def test_sales_rejects_neither(app_client):
    """POST with neither items nor text → 422."""
    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_none",
            "date": "2026-04-14",
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Task 8-03-02: Hebrew free-text path
# ---------------------------------------------------------------------------


def test_hebrew_text(app_client):
    """POST with Hebrew free text parses and persists two rows."""
    # Pre-create merchant
    resp = app_client.post("/merchants", json={"merchant_id": "shop_hebrew"})
    assert resp.status_code == 201

    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_hebrew",
            "date": "2026-04-14",
            "text": "20 עגבניות, 5 מלפפונים",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted_rows"] == 2
    assert body["skipped"] == []

    from meshek_ml.storage.merchant_store import MerchantStore

    with MerchantStore("shop_hebrew") as store:
        df = store.read_sales()

    assert len(df) == 2
    products = set(df["product"].tolist())
    assert products <= {"tomato", "cucumber"}


# ---------------------------------------------------------------------------
# Task 8-03-03: partial-success semantics
# ---------------------------------------------------------------------------


def test_partial(app_client):
    """POST with one bad line → 200, accepted_rows=2, skipped list has 1 entry."""
    # Pre-create merchant
    resp = app_client.post("/merchants", json={"merchant_id": "shop_partial"})
    assert resp.status_code == 201

    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_partial",
            "date": "2026-04-14",
            "text": "20 עגבניות, שקל רע, 5 מלפפונים",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted_rows"] == 2
    assert len(body["skipped"]) == 1
    assert isinstance(body["skipped"][0]["reason"], str)
    assert body["skipped"][0]["reason"] != ""


def test_all_fail(app_client):
    """POST where all lines fail → 422."""
    # Pre-create merchant
    resp = app_client.post("/merchants", json={"merchant_id": "shop_allfail"})
    assert resp.status_code == 201

    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "shop_allfail",
            "date": "2026-04-14",
            "text": "bogus bogus",
        },
    )
    assert resp.status_code == 422


def test_sales_unknown_merchant(app_client):
    """POST against a merchant that was never created → 404 or 500 until plan 05."""
    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "nonexistent_merchant",
            "date": "2026-04-14",
            "items": [{"product_id": "tomato", "quantity": 10, "unit": "kg"}],
        },
    )
    # plan 05 will map UnknownMerchantError → 404; until then raw 500 is acceptable
    assert resp.status_code in (404, 500)
