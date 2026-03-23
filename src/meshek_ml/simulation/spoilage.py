"""Weibull spoilage model and FIFO inventory tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.stats import weibull_min


def weibull_quality(
    age_days: int | np.ndarray,
    shape: float = 2.0,
    scale: float = 5.0,
) -> float | np.ndarray:
    """Compute product quality as a function of age using Weibull decay.

    quality(t) = exp(-(t/scale)^shape)

    Args:
        age_days: Age in days (scalar or array).
        shape: Weibull shape parameter (beta). >1 means accelerating deterioration.
        scale: Weibull scale parameter (eta), related to expected shelf life.

    Returns:
        Quality score between 0 and 1.
    """
    return np.exp(-((np.asarray(age_days) / scale) ** shape))


def shelf_life_distribution(
    shape: float = 2.0,
    scale: float = 5.0,
    quality_threshold: float = 0.3,
    n_samples: int = 1000,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Sample shelf life durations from a Weibull distribution.

    Args:
        shape: Weibull shape parameter.
        scale: Weibull scale parameter.
        quality_threshold: Quality level below which product is considered spoiled.
        n_samples: Number of samples.
        rng: Random generator.

    Returns:
        Array of shelf life durations in days.
    """
    if rng is None:
        rng = np.random.default_rng()
    samples = weibull_min.rvs(shape, scale=scale, size=n_samples, random_state=rng)
    return np.maximum(np.round(samples), 1).astype(int)


@dataclass
class Batch:
    """A batch of product with a specific age."""

    quantity: int
    age_days: int = 0


@dataclass
class FIFOInventory:
    """FIFO inventory tracker for perishable goods.

    Tracks inventory as a list of batches ordered by age (oldest first).
    Sells oldest stock first, removes expired batches daily.
    """

    max_shelf_life: int = 7
    batches: list[Batch] = field(default_factory=list)

    @property
    def total_stock(self) -> int:
        """Total units across all batches."""
        return sum(b.quantity for b in self.batches)

    def receive(self, quantity: int) -> None:
        """Receive a new delivery (age = 0 days)."""
        if quantity > 0:
            self.batches.append(Batch(quantity=quantity, age_days=0))

    def age_and_expire(self) -> int:
        """Age all batches by one day and remove expired ones.

        Returns:
            Number of units wasted (expired).
        """
        wasted = 0
        remaining = []
        for batch in self.batches:
            batch.age_days += 1
            if batch.age_days > self.max_shelf_life:
                wasted += batch.quantity
            else:
                remaining.append(batch)
        self.batches = remaining
        return wasted

    def sell(self, demand: int) -> tuple[int, int]:
        """Sell units using FIFO (oldest first).

        Args:
            demand: Number of units demanded.

        Returns:
            Tuple of (units_sold, unmet_demand).
        """
        sold = 0
        remaining_demand = demand

        while remaining_demand > 0 and self.batches:
            batch = self.batches[0]
            if batch.quantity <= remaining_demand:
                sold += batch.quantity
                remaining_demand -= batch.quantity
                self.batches.pop(0)
            else:
                batch.quantity -= remaining_demand
                sold += remaining_demand
                remaining_demand = 0

        return sold, remaining_demand
