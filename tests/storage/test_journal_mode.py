"""Regression tests for D-10/D-11: PRAGMA journal_mode=DELETE + synchronous=FULL.

GCS FUSE cannot honor WAL mode (RESEARCH §PRAGMA). MerchantStore must force
DELETE journal + FULL sync unconditionally on every freshly opened connection.
"""
from __future__ import annotations

from meshek_ml.storage.merchant_store import MerchantStore


def test_journal_mode_is_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_DATA_DIR", str(tmp_path))
    with MerchantStore("probe_shop") as store:
        mode = store._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "delete", f"expected journal_mode=delete, got {mode!r}"


def test_synchronous_full(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_DATA_DIR", str(tmp_path))
    with MerchantStore("probe_shop") as store:
        sync = store._conn.execute("PRAGMA synchronous").fetchone()[0]
        # 2 == FULL per sqlite docs
        assert sync == 2, f"expected synchronous=FULL(2), got {sync!r}"
