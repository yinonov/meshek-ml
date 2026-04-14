"""Public API for the storage package."""
from __future__ import annotations
from pathlib import Path

from meshek_ml.storage.merchant_store import (
    InvalidMerchantIdError,
    MerchantProfile,
    MerchantStore,
    MerchantStoreError,
    UnknownMerchantError,
    _data_root,
)

__all__ = [
    "MerchantStore",
    "MerchantProfile",
    "MerchantStoreError",
    "UnknownMerchantError",
    "InvalidMerchantIdError",
    "get_data_root",
]


def get_data_root() -> Path:
    """Resolve the merchant data root (public wrapper around _data_root).

    Downstream packages (e.g., recommendation.pooled_store) must use this
    helper rather than reaching into the private _data_root symbol.
    """
    return _data_root()
