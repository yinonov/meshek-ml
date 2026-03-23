"""Tests for the simulation orchestrator."""

import pytest

from meshek_ml.simulation.generator import run_simulation


@pytest.mark.slow
def test_run_simulation_full():
    df = run_simulation(n_merchants=2, start_date="2024-01-01", end_date="2024-01-31", seed=42)
    assert len(df) > 0
    assert "merchant_id" in df.columns
    assert "product" in df.columns
    assert "realized_demand" in df.columns
    # 2 merchants x 8 products x 31 days = 496 rows
    assert len(df) == 2 * 8 * 31
