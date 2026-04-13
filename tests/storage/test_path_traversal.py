"""T-5-01: merchant_id whitelist + path-traversal defense in depth."""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "bad_id",
    [
        "",                       # empty
        "   ",                    # whitespace only
        "../evil",                # parent escape
        "../../etc/passwd",       # deep traversal
        "a/b",                    # path separator
        "a\\b",                   # windows separator
        "a\x00b",                 # null byte
        "shop with space",        # space
        "shop.a",                 # dot
        "x" * 65,                 # too long (>64)
        "café",                   # non-ASCII
        ".",                      # just a dot
        "..",                     # just dotdot
        "/absolute",              # absolute path
    ],
)
def test_merchant_id_whitelist_rejects_unsafe(data_root, bad_id):
    from meshek_ml.storage.merchant_store import MerchantStore, InvalidMerchantIdError
    with pytest.raises(InvalidMerchantIdError):
        MerchantStore(bad_id)


@pytest.mark.parametrize(
    "good_id",
    [
        "shop_a",
        "SHOP-42",
        "merchant_001",
        "a",
        "x" * 64,  # max length
        "abc-DEF_123",
    ],
)
def test_merchant_id_whitelist_accepts_safe(data_root, good_id):
    from meshek_ml.storage.merchant_store import MerchantStore
    with MerchantStore(good_id) as store:
        assert store.merchant_id == good_id


def test_path_traversal_does_not_create_files_outside_root(data_root, tmp_path):
    """Defense in depth: even if regex were bypassed, Path.resolve() parent check catches it."""
    from meshek_ml.storage.merchant_store import MerchantStore, InvalidMerchantIdError
    with pytest.raises(InvalidMerchantIdError):
        MerchantStore("../../../tmp/pwned")
    # Ensure no stray .sqlite was created anywhere under tmp_path
    strays = list(tmp_path.rglob("pwned*.sqlite"))
    assert strays == []
