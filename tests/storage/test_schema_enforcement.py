"""STOR-01 #4: fail-fast canonical schema enforcement on writes."""
from __future__ import annotations

import pandas as pd
import pytest


def test_write_rejects_missing_columns(data_root):
    from meshek_ml.storage.merchant_store import MerchantStore
    from meshek_ml.forecasting.schema import SchemaValidationError
    bad = pd.DataFrame({"date": ["2026-04-10"], "product": ["tomato"]})  # missing merchant_id, quantity
    with MerchantStore("shop_a") as store:
        with pytest.raises(SchemaValidationError):
            store.write_sales(bad)


def test_write_rejects_null_values(data_root):
    from meshek_ml.storage.merchant_store import MerchantStore
    from meshek_ml.forecasting.schema import SchemaValidationError
    bad = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-10"]),
        "merchant_id": ["shop_a"],
        "product": ["tomato"],
        "quantity": [None],
    })
    with MerchantStore("shop_a") as store:
        with pytest.raises(SchemaValidationError):
            store.write_sales(bad)


def test_write_rejects_foreign_merchant_id(data_root):
    """A DataFrame with merchant_id != store.merchant_id must be rejected."""
    from meshek_ml.storage.merchant_store import MerchantStore
    from meshek_ml.forecasting.schema import SchemaValidationError
    df = pd.DataFrame({
        "date": pd.to_datetime(["2026-04-10"]),
        "merchant_id": ["shop_b"],  # foreign!
        "product": ["tomato"],
        "quantity": [10.0],
    })
    with MerchantStore("shop_a") as store:
        with pytest.raises(SchemaValidationError):
            store.write_sales(df)
