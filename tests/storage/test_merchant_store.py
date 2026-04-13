"""Tests for MerchantStore: profile CRUD, sales round-trip, date dtype, upsert."""
from __future__ import annotations

import pandas as pd
import pytest


def test_profile_roundtrip(data_root):
    from meshek_ml.storage.merchant_store import MerchantProfile, MerchantStore
    with MerchantStore("shop_a") as store:
        store.create_profile(MerchantProfile(merchant_id="shop_a", name="Shop A"))
        profile = store.get_profile()
    assert profile is not None
    assert profile.merchant_id == "shop_a"
    assert profile.name == "Shop A"
    assert profile.timezone == "Asia/Jerusalem"
    assert profile.language == "he"
    assert profile.created_at  # ISO-8601 auto-set


def test_profile_defaults_zero_config(data_root):
    """STOR-02: only merchant_id is required; sensible defaults for the rest."""
    from meshek_ml.storage.merchant_store import MerchantProfile, MerchantStore
    with MerchantStore("shop_b") as store:
        store.create_profile(MerchantProfile(merchant_id="shop_b"))
        profile = store.get_profile()
    assert profile.timezone == "Asia/Jerusalem"
    assert profile.language == "he"
    assert profile.name is None


def test_get_profile_returns_none_when_missing(data_root):
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore("shop_c") as store:
        assert store.get_profile() is None


def test_reader_rejects_unknown_merchant(data_root):
    """D-03: lazy-create-on-read is forbidden — must raise loudly."""
    from meshek_ml.storage.merchant_store import MerchantStore, UnknownMerchantError
    with pytest.raises(UnknownMerchantError):
        MerchantStore("never_created", must_exist=True)


def test_sales_roundtrip(data_root, sample_sales_df):
    """STOR-01 #3: round-trip preserves date, merchant_id, product, quantity."""
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore("shop_a") as store:
        n = store.write_sales(sample_sales_df)
        out = store.read_sales()
    assert n == 3
    assert list(out.columns) == ["date", "merchant_id", "product", "quantity"]
    assert len(out) == 3
    assert set(out["product"]) == {"tomato", "cucumber"}
    assert out.loc[out["product"] == "cucumber", "quantity"].iloc[0] == 8.0


def test_read_sales_date_dtype(data_root, sample_sales_df):
    """Pitfall 1: date must round-trip as datetime64[ns], not object."""
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore("shop_a") as store:
        store.write_sales(sample_sales_df)
        out = store.read_sales()
    assert str(out["date"].dtype) == "datetime64[ns]"


def test_read_sales_date_range(data_root, sample_sales_df):
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore("shop_a") as store:
        store.write_sales(sample_sales_df)
        out = store.read_sales(start="2026-04-11", end="2026-04-11")
    assert len(out) == 1
    assert out["product"].iloc[0] == "tomato"
    assert out["quantity"].iloc[0] == 14.0


def test_sales_upsert_overwrites_same_date_product(data_root):
    """D-05: re-writing (date, product) overwrites quantity, does not append."""
    from meshek_ml.storage.merchant_store import MerchantStore
    df1 = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-10"]),
        "merchant_id": ["shop_a"],
        "product": ["tomato"],
        "quantity": [10.0],
    })
    df2 = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-10"]),
        "merchant_id": ["shop_a"],
        "product": ["tomato"],
        "quantity": [99.0],
    })
    with MerchantStore("shop_a") as store:
        store.write_sales(df1)
        store.write_sales(df2)
        out = store.read_sales()
    assert len(out) == 1
    assert out["quantity"].iloc[0] == 99.0


def test_reopen_idempotent(data_root, sample_sales_df):
    """D-07: re-opening an existing store does not re-run migrations or lose data."""
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore("shop_a") as store:
        store.write_sales(sample_sales_df)
    with MerchantStore("shop_a") as store:
        out = store.read_sales()
    assert len(out) == 3
