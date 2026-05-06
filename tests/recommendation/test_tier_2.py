"""Tests for tier_2_pooled_priors (D-05 shrinkage, D-06 linear confidence)."""
from __future__ import annotations

import pandas as pd
import pytest

from meshek_ml.recommendation.pooled_store import PooledStore
from meshek_ml.recommendation.tiers import tier_2_pooled_priors


class _StubPooled:
    """Lightweight PooledStore stub for pure-arithmetic tests."""

    def __init__(self, means: dict[str, float]) -> None:
        self._means = means

    def pooled_mean_by_product(
        self, exclude_merchant_id: str
    ) -> dict[str, float]:
        return dict(self._means)


def _own_df(merchant_id: str, product: str, qty: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-10"]),
            "merchant_id": [merchant_id],
            "product": [product],
            "quantity": [qty],
        }
    )


def test_reasoning_tier():
    pooled = _StubPooled({"tomato": 10.0})
    resp = tier_2_pooled_priors(
        "M", _own_df("M", "tomato", 20.0), pooled, n_days=7
    )
    assert resp.recommendations[0].reasoning_tier == "pooled_prior"


def test_confidence_bounds():
    pooled = _StubPooled({"tomato": 10.0})
    df = _own_df("M", "tomato", 20.0)
    r1 = tier_2_pooled_priors("M", df, pooled, n_days=1)
    r13 = tier_2_pooled_priors("M", df, pooled, n_days=13)
    assert r1.recommendations[0].confidence_score == pytest.approx(0.3, abs=1e-6)
    assert r13.recommendations[0].confidence_score == pytest.approx(0.6, abs=1e-6)


def test_confidence_monotonic():
    pooled = _StubPooled({"tomato": 10.0})
    df = _own_df("M", "tomato", 20.0)
    scores = [
        tier_2_pooled_priors("M", df, pooled, n_days=n).recommendations[0].confidence_score
        for n in range(1, 14)
    ]
    assert scores == sorted(scores)
    assert all(b > a for a, b in zip(scores, scores[1:]))


def test_shrinkage_weights():
    pooled = _StubPooled({"tomato": 10.0})
    df = _own_df("M", "tomato", 20.0)
    # n_days=7 -> shrink = 7/21 = 1/3 -> q = (1/3)*20 + (2/3)*10 = 40/3 ≈ 13.33
    resp = tier_2_pooled_priors("M", df, pooled, n_days=7)
    rec = resp.recommendations[0]
    assert rec.product_id == "tomato"
    assert rec.predicted_demand == pytest.approx(round(40 / 3, 4), abs=1e-6)


def test_uses_pooled_store(data_root, merchant_store_factory):
    merchant_store_factory("A", days=14, products=["tomato"], qty=10.0)
    merchant_store_factory("B", days=14, products=["tomato"], qty=20.0)
    merchant_store_factory("M", days=7, products=["tomato"], qty=30.0)

    pooled = PooledStore()
    with_m_sales = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-04-10"] * 7),
            "merchant_id": ["M"] * 7,
            "product": ["tomato"] * 7,
            "quantity": [30.0] * 7,
        }
    )
    resp = tier_2_pooled_priors("M", with_m_sales, pooled, n_days=7)
    # pooled excluding M = 15; shrink = 7/21 = 1/3; q = 1/3*30 + 2/3*15 = 20.0
    assert len(resp.recommendations) == 1
    assert resp.recommendations[0].predicted_demand == pytest.approx(20.0, abs=1e-2)


def test_merchant_id_propagated():
    pooled = _StubPooled({"tomato": 10.0})
    resp = tier_2_pooled_priors(
        "shop_xyz", _own_df("shop_xyz", "tomato", 20.0), pooled, n_days=5
    )
    assert resp.merchant_id == "shop_xyz"
