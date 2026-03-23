"""Classical newsvendor model for perishable inventory."""

from __future__ import annotations

from scipy.stats import nbinom, norm


def critical_fractile(
    underage_cost: float,
    overage_cost: float,
) -> float:
    """Compute the newsvendor critical fractile.

    tau = Cu / (Cu + Co)

    Args:
        underage_cost: Cost per unit of unmet demand (lost margin).
        overage_cost: Cost per unit of excess (waste at purchase cost minus salvage).

    Returns:
        Optimal service level (quantile) to order at.
    """
    return underage_cost / (underage_cost + overage_cost)


def optimal_order_normal(
    mean_demand: float,
    std_demand: float,
    underage_cost: float,
    overage_cost: float,
) -> float:
    """Compute optimal order quantity assuming Normal demand.

    Q* = mu + z_tau * sigma

    Args:
        mean_demand: Expected daily demand.
        std_demand: Standard deviation of daily demand.
        underage_cost: Cost per unit of stockout.
        overage_cost: Cost per unit of waste.

    Returns:
        Optimal order quantity.
    """
    tau = critical_fractile(underage_cost, overage_cost)
    z = norm.ppf(tau)
    return max(0, mean_demand + z * std_demand)


def optimal_order_negbin(
    mean_demand: float,
    dispersion: float,
    underage_cost: float,
    overage_cost: float,
) -> int:
    """Compute optimal order quantity assuming Negative Binomial demand.

    Q* = F_NB^{-1}(tau)

    Args:
        mean_demand: Expected daily demand.
        dispersion: NB dispersion parameter (n).
        underage_cost: Cost per unit of stockout.
        overage_cost: Cost per unit of waste.

    Returns:
        Optimal order quantity (integer).
    """
    tau = critical_fractile(underage_cost, overage_cost)
    n = dispersion
    p = n / (n + mean_demand)
    return int(nbinom.ppf(tau, n=n, p=p))
