"""STOR-01 #1: per-merchant filesystem isolation."""
from __future__ import annotations

import pandas as pd


def test_filesystem_isolation(data_root):
    """Two merchants must land in two distinct .sqlite files."""
    from meshek_ml.storage.merchant_store import MerchantStore, MerchantProfile
    with MerchantStore("shop_a") as a:
        a.create_profile(MerchantProfile(merchant_id="shop_a"))
    with MerchantStore("shop_b") as b:
        b.create_profile(MerchantProfile(merchant_id="shop_b"))
    files = sorted(p.name for p in data_root.glob("*.sqlite"))
    assert files == ["shop_a.sqlite", "shop_b.sqlite"]


def test_isolation_no_data_bleed(data_root):
    """Sales written to shop_a are invisible to shop_b."""
    from meshek_ml.storage.merchant_store import MerchantStore
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-10"]),
        "merchant_id": ["shop_a"],
        "product": ["tomato"],
        "quantity": [10.0],
    })
    with MerchantStore("shop_a") as a:
        a.write_sales(df)
    with MerchantStore("shop_b") as b:
        out = b.read_sales()
    assert len(out) == 0
