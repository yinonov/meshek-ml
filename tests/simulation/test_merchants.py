"""Tests for merchant generation."""

from meshek_ml.simulation.merchants import generate_merchants


def test_generate_merchants_count():
    merchants = generate_merchants(n_merchants=5, seed=42)
    assert len(merchants) == 5


def test_generate_merchants_unique_ids():
    merchants = generate_merchants(n_merchants=10, seed=42)
    ids = [m.merchant_id for m in merchants]
    assert len(set(ids)) == 10
