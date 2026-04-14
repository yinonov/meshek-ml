"""Cross-merchant filesystem-scan aggregator used by Tier 2 pooled priors.

Scans ``MESHEK_DATA_DIR`` for ``*.sqlite`` files (excluding WAL/SHM
sidecars — Pitfall 5) and computes product-level means across merchants
with at least ``MIN_HISTORY_DAYS_FOR_PRIOR`` distinct sale dates.

Security notes:
    T-6-04: ``Path.glob("*.sqlite")`` is exact-suffix; WAL/SHM files end
        in ``.sqlite-wal``/``.sqlite-shm`` and are not matched. Each stem
        is re-validated through ``_validate_merchant_id``; invalid names
        are silently skipped so stray files never crash the scan.
    T-6-05: ``pooled_mean_by_product`` requires ``exclude_merchant_id``
        so callers must explicitly name the merchant whose data must not
        appear in the aggregate.
"""
from __future__ import annotations

from meshek_ml.storage import get_data_root
from meshek_ml.storage.merchant_store import (
    InvalidMerchantIdError,
    MerchantStore,
    _validate_merchant_id,
)


def _validate_merchant_id_safely(stem: str) -> bool:
    try:
        _validate_merchant_id(stem)
    except InvalidMerchantIdError:
        return False
    return True


class PooledStore:
    """Filesystem-scan aggregator over all merchant SQLite files."""

    MIN_HISTORY_DAYS_FOR_PRIOR: int = 14

    def list_merchant_ids(self) -> list[str]:
        """Return sorted merchant IDs for every valid ``*.sqlite`` under root."""
        root = get_data_root()
        return sorted(
            p.stem
            for p in root.glob("*.sqlite")
            if _validate_merchant_id_safely(p.stem)
        )

    def pooled_mean_by_product(
        self, exclude_merchant_id: str
    ) -> dict[str, float]:
        """Average per-product daily quantity across eligible merchants.

        Skips ``exclude_merchant_id`` entirely (T-6-05) and any merchant
        with fewer than ``MIN_HISTORY_DAYS_FOR_PRIOR`` distinct dates.
        Returns an empty dict when no eligible merchants exist.
        """
        per_product: dict[str, list[float]] = {}
        for mid in self.list_merchant_ids():
            if mid == exclude_merchant_id:
                continue
            try:
                with MerchantStore(mid, must_exist=True) as store:
                    sales = store.read_sales()
            except Exception:
                # Defensive: a corrupt or unreadable sidecar file must
                # never break the whole scan.
                continue
            if sales.empty:
                continue
            if sales["date"].nunique() < self.MIN_HISTORY_DAYS_FOR_PRIOR:
                continue
            means = sales.groupby("product")["quantity"].mean()
            for product, value in means.items():
                per_product.setdefault(str(product), []).append(float(value))

        if not per_product:
            return {}
        return {p: sum(vs) / len(vs) for p, vs in per_product.items()}
