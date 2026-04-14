"""Tests for POST /merchants endpoint (API-02, plan 08-02)."""
from __future__ import annotations

import re


def test_create_explicit_id(app_client, data_dir):
    """POST with explicit valid merchant_id returns 201 and echoes the id."""
    resp = app_client.post(
        "/merchants",
        json={"merchant_id": "shop_a", "display_name": "Shop A"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["merchant_id"] == "shop_a"


def test_invalid_id_rejected_before_fs(app_client, data_dir):
    """T-5-01: path-traversal id returns 422 with zero filesystem side-effects."""
    merchants_dir = data_dir / "merchants"
    resp = app_client.post(
        "/merchants",
        json={"merchant_id": "../etc/passwd"},
    )
    assert resp.status_code == 422
    # Assert no SQLite file was created in merchants_dir
    sqlite_files = list(merchants_dir.glob("*.sqlite"))
    assert sqlite_files == [], f"Unexpected SQLite files: {sqlite_files}"


def test_invalid_id_slash(app_client, data_dir):
    """merchant_id containing '/' returns 422."""
    resp = app_client.post(
        "/merchants",
        json={"merchant_id": "a/b"},
    )
    assert resp.status_code == 422


def test_invalid_id_too_long(app_client, data_dir):
    """merchant_id exceeding 64 chars returns 422."""
    resp = app_client.post(
        "/merchants",
        json={"merchant_id": "a" * 65},
    )
    assert resp.status_code == 422


def test_auto_id(app_client, data_dir):
    """POST without merchant_id returns a 32-char hex id; two calls differ."""
    resp1 = app_client.post("/merchants", json={"display_name": "Anon"})
    assert resp1.status_code == 201
    body1 = resp1.json()
    mid1 = body1["merchant_id"]
    assert len(mid1) == 32, f"Expected 32-char hex, got {len(mid1)}: {mid1!r}"
    # Must be a valid hex string
    int(mid1, 16)
    # Must match the merchant_id pattern
    assert re.match(r"^[A-Za-z0-9_-]{1,64}$", mid1)

    resp2 = app_client.post("/merchants", json={"display_name": "Anon2"})
    assert resp2.status_code == 201
    mid2 = resp2.json()["merchant_id"]
    assert mid1 != mid2, "Two successive auto-id calls must produce distinct ids"
