"""Tests for PooledStore filesystem scan and pooled aggregation."""
from __future__ import annotations

from meshek_ml.recommendation.pooled_store import PooledStore


def test_list_merchant_ids_excludes_sidecars(data_root):
    # Create real empty files (WAL/SHM sidecars and valid stores)
    (data_root / "foo.sqlite").write_bytes(b"")
    (data_root / "foo.sqlite-wal").write_bytes(b"")
    (data_root / "foo.sqlite-shm").write_bytes(b"")
    (data_root / "bar.sqlite").write_bytes(b"")

    store = PooledStore()
    assert store.list_merchant_ids() == ["bar", "foo"]


def test_list_merchant_ids_empty_root(data_root):
    assert PooledStore().list_merchant_ids() == []


def test_excludes_self(data_root, merchant_store_factory):
    merchant_store_factory("A", days=14, products=["tomato"], qty=10.0)
    merchant_store_factory("B", days=14, products=["tomato"], qty=10.0)
    merchant_store_factory("C", days=14, products=["tomato"], qty=100.0)

    result = PooledStore().pooled_mean_by_product(exclude_merchant_id="C")
    assert result == {"tomato": 10.0}


def test_skips_low_history(data_root, merchant_store_factory):
    merchant_store_factory("A", days=14, products=["tomato"], qty=10.0)
    merchant_store_factory("B", days=5, products=["tomato"], qty=100.0)

    result = PooledStore().pooled_mean_by_product(exclude_merchant_id="C")
    assert result == {"tomato": 10.0}


def test_invalid_merchant_id_in_file(data_root, merchant_store_factory):
    merchant_store_factory("A", days=14, products=["tomato"], qty=10.0)
    # Dots violate the `^[A-Za-z0-9_-]{1,64}$` whitelist.
    (data_root / "bad..name.sqlite").write_bytes(b"")

    ids = PooledStore().list_merchant_ids()
    assert "A" in ids
    assert "bad..name" not in ids
