"""Tests for data partitioning."""

import pandas as pd

from meshek_ml.federated.partitioning import create_iid_partitions, partition_by_merchant


def test_partition_by_merchant():
    df = pd.DataFrame(
        {
            "merchant_id": ["A", "A", "B", "B", "C"],
            "value": [1, 2, 3, 4, 5],
        }
    )
    parts = partition_by_merchant(df)
    assert len(parts) == 3
    assert len(parts["A"]) == 2
    assert len(parts["C"]) == 1


def test_iid_partitions():
    df = pd.DataFrame({"value": range(100)})
    parts = create_iid_partitions(df, n_partitions=4)
    assert len(parts) == 4
    total = sum(len(p) for p in parts.values())
    assert total == 100
