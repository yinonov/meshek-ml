"""Custom Gymnasium environment for perishable inventory management."""

from __future__ import annotations

from typing import Any, ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from meshek_ml.optimization.rewards import CostParams, compute_reward
from meshek_ml.simulation.spoilage import FIFOInventory


class PerishableInventoryEnv(gym.Env):
    """Gymnasium environment for single-product perishable inventory.

    State: [inventory_by_age_bucket..., recent_demand_history..., day_of_week]
    Action: order quantity (continuous, clipped to [0, max_order])
    Reward: profit minus waste/stockout penalties

    Args:
        max_shelf_life: Maximum product shelf life in days.
        max_order: Maximum units that can be ordered per day.
        demand_mean: Mean daily demand for demand generation.
        demand_dispersion: Negative Binomial dispersion parameter.
        episode_length: Number of days per episode.
        costs: Cost parameters for reward computation.
    """

    metadata: ClassVar[dict[str, list[str]]] = {"render_modes": ["human"]}

    def __init__(
        self,
        max_shelf_life: int = 7,
        max_order: int = 50,
        demand_mean: float = 20.0,
        demand_dispersion: float = 3.0,
        episode_length: int = 90,
        costs: CostParams | None = None,
    ):
        super().__init__()
        self.max_shelf_life = max_shelf_life
        self.max_order = max_order
        self.demand_mean = demand_mean
        self.demand_dispersion = demand_dispersion
        self.episode_length = episode_length
        self.costs = costs or CostParams()

        # State: shelf_life buckets + 7 demand history + day_of_week (one-hot 7)
        state_dim = max_shelf_life + 7 + 7
        self.observation_space = spaces.Box(
            low=0, high=np.inf, shape=(state_dim,), dtype=np.float32
        )

        # Action: continuous order quantity
        self.action_space = spaces.Box(
            low=np.array([0.0]), high=np.array([float(max_order)]), dtype=np.float32
        )

        self.inventory = FIFOInventory(max_shelf_life=max_shelf_life)
        self.demand_history: list[int] = []
        self.current_step = 0
        self.current_day_of_week = 0

    def _get_obs(self) -> np.ndarray:
        """Build observation vector from current state."""
        # Inventory by age bucket
        age_buckets = np.zeros(self.max_shelf_life, dtype=np.float32)
        for batch in self.inventory.batches:
            idx = min(batch.age_days, self.max_shelf_life - 1)
            age_buckets[idx] += batch.quantity

        # Recent demand (last 7 days, zero-padded)
        recent = np.zeros(7, dtype=np.float32)
        for i, d in enumerate(self.demand_history[-7:]):
            recent[i] = d

        # Day of week one-hot
        dow = np.zeros(7, dtype=np.float32)
        dow[self.current_day_of_week] = 1.0

        return np.concatenate([age_buckets, recent, dow])

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[np.ndarray, dict]:
        """Reset the environment to initial state."""
        super().reset(seed=seed)
        self.inventory = FIFOInventory(max_shelf_life=self.max_shelf_life)
        self.demand_history = []
        self.current_step = 0
        self.current_day_of_week = 0
        # Start with some initial stock
        self.inventory.receive(int(self.demand_mean))
        return self._get_obs(), {}

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one day of inventory management.

        Order of operations:
        1. Receive yesterday's order
        2. Generate today's demand
        3. Sell (FIFO)
        4. Age inventory and remove expired
        5. Place new order (the action)
        6. Compute reward
        """
        order_qty = int(np.clip(action[0], 0, self.max_order))

        # 1. Receive delivery (ordered yesterday)
        self.inventory.receive(order_qty)

        # 2. Generate demand
        n = self.demand_dispersion
        p = n / (n + self.demand_mean)
        demand = self.np_random.negative_binomial(n=n, p=p)

        # 3. Sell FIFO
        sold, unmet = self.inventory.sell(demand)

        # 4. Age and expire
        wasted = self.inventory.age_and_expire()

        # 5. Record
        self.demand_history.append(demand)
        self.current_step += 1
        self.current_day_of_week = (self.current_day_of_week + 1) % 7

        # 6. Compute reward
        reward = compute_reward(
            units_sold=sold,
            units_ordered=order_qty,
            units_held=self.inventory.total_stock,
            units_wasted=wasted,
            unmet_demand=unmet,
            costs=self.costs,
        )

        terminated = self.current_step >= self.episode_length
        info = {
            "demand": demand,
            "sold": sold,
            "wasted": wasted,
            "unmet_demand": unmet,
            "stock": self.inventory.total_stock,
        }

        return self._get_obs(), reward, terminated, False, info
