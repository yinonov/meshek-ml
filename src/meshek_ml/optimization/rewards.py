"""Asymmetric reward functions for inventory RL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostParams:
    """Cost parameters for inventory reward computation."""

    selling_price: float = 7.0
    purchase_cost: float = 5.0
    holding_cost: float = 0.1
    waste_penalty: float = 5.0  # Full purchase cost for spoiled items
    stockout_penalty: float = 3.0  # Lost margin + goodwill cost


def compute_reward(
    units_sold: int,
    units_ordered: int,
    units_held: int,
    units_wasted: int,
    unmet_demand: int,
    costs: CostParams | None = None,
) -> float:
    """Compute single-period inventory reward.

    R = revenue - purchase_cost - holding_cost - waste_penalty - stockout_penalty

    Args:
        units_sold: Units sold to customers.
        units_ordered: Units ordered (new delivery).
        units_held: Units remaining in inventory at end of day.
        units_wasted: Units spoiled/expired.
        unmet_demand: Demand that could not be fulfilled.
        costs: Cost parameters.

    Returns:
        Scalar reward value.
    """
    if costs is None:
        costs = CostParams()

    revenue = units_sold * costs.selling_price
    purchase = units_ordered * costs.purchase_cost
    holding = units_held * costs.holding_cost
    waste = units_wasted * costs.waste_penalty
    stockout = unmet_demand * costs.stockout_penalty

    return revenue - purchase - holding - waste - stockout
