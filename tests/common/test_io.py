"""Tests for IO utilities."""

import pandas as pd

from meshek_ml.common.io import load_parquet, save_parquet


def test_parquet_roundtrip(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    path = tmp_path / "test.parquet"
    save_parquet(df, path)
    loaded = load_parquet(path)
    pd.testing.assert_frame_equal(df, loaded)
