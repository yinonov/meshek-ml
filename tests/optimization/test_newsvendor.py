"""Tests for newsvendor model."""

from meshek_ml.optimization.newsvendor import critical_fractile, optimal_order_negbin


def test_critical_fractile():
    # Cu=2, Co=5 -> tau = 2/7
    tau = critical_fractile(underage_cost=2.0, overage_cost=5.0)
    assert abs(tau - 2 / 7) < 1e-6


def test_optimal_order_negbin_conservative():
    # With high overage cost, order should be below mean
    order = optimal_order_negbin(
        mean_demand=20.0, dispersion=3.0, underage_cost=2.0, overage_cost=5.0
    )
    assert order < 20
    assert order > 0
