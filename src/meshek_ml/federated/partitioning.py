"""Merchant-based data partitioning for federated learning."""

from __future__ import annotations

import pandas as pd


def partition_by_merchant(
    data: pd.DataFrame,
    merchant_col: str = "merchant_id",
) -> dict[str, pd.DataFrame]:
    """Split dataset into per-merchant partitions.

    Simulates federated data silos where each merchant only has access
    to their own sales data.

    Args:
        data: Full synthetic dataset.
        merchant_col: Column identifying the merchant.

    Returns:
        Dictionary mapping merchant_id to their local DataFrame.
    """
    return {mid: group.copy() for mid, group in data.groupby(merchant_col)}


def create_iid_partitions(
    data: pd.DataFrame,
    n_partitions: int,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """Create IID partitions for sanity-check experiments.

    Randomly shuffles data and splits evenly, ignoring merchant identity.
    Used to compare IID vs natural non-IID federated performance.

    Args:
        data: Full dataset.
        n_partitions: Number of equal partitions.
        seed: Random seed.

    Returns:
        Dictionary mapping partition ID to DataFrame.
    """
    shuffled = data.sample(frac=1, random_state=seed).reset_index(drop=True)
    chunk_size = len(shuffled) // n_partitions
    partitions = {}
    for i in range(n_partitions):
        start = i * chunk_size
        end = start + chunk_size if i < n_partitions - 1 else len(shuffled)
        partitions[f"partition_{i:03d}"] = shuffled.iloc[start:end].copy()
    return partitions
