"""Inventory optimization evaluation metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meshek_ml.common.types import MetricsDict


def compute_inventory_metrics(
    total_demand: int,
    total_sold: int,
    total_wasted: int,
    total_ordered: int,
    total_stockout_events: int,
    n_days: int,
) -> MetricsDict:
    """Compute inventory performance metrics.

    Args:
        total_demand: Total units demanded over the period.
        total_sold: Total units successfully sold.
        total_wasted: Total units spoiled/expired.
        total_ordered: Total units ordered.
        total_stockout_events: Number of days with unmet demand.
        n_days: Number of days in the evaluation period.

    Returns:
        Dictionary of metric name to value.
    """
    fill_rate = total_sold / total_demand if total_demand > 0 else 1.0
    waste_rate = total_wasted / total_ordered if total_ordered > 0 else 0.0
    stockout_frequency = total_stockout_events / n_days if n_days > 0 else 0.0

    return {
        "fill_rate": fill_rate,
        "waste_rate": waste_rate,
        "stockout_frequency": stockout_frequency,
        "total_sold": float(total_sold),
        "total_wasted": float(total_wasted),
        "total_ordered": float(total_ordered),
    }
