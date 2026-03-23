"""Hydra structured configs for all pillars."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulationConfig:
    """Configuration for synthetic data generation."""

    seed: int = 42
    n_merchants: int = 10
    n_products: int = 8
    start_date: str = "2023-01-01"
    end_date: str = "2024-12-31"
    output_dir: str = "data/synthetic"


@dataclass
class DemandConfig:
    """Parameters for demand distribution generation."""

    base_distribution: str = "negative_binomial"
    dispersion: float = 3.0
    weekly_pattern: dict[str, float] = field(
        default_factory=lambda: {
            "monday": 0.85,
            "tuesday": 0.90,
            "wednesday": 0.95,
            "thursday": 1.00,
            "friday": 1.15,
            "saturday": 1.30,
            "sunday": 0.70,
        }
    )


@dataclass
class ForecastingConfig:
    """Configuration for demand forecasting models."""

    model: str = "lightgbm"
    horizon: int = 3
    lag_features: list[int] = field(default_factory=lambda: [1, 7, 14, 28])
    rolling_windows: list[int] = field(default_factory=lambda: [7, 14, 28])
    quantiles: list[float] = field(default_factory=lambda: [0.1, 0.25, 0.5, 0.75, 0.9])


@dataclass
class OptimizationConfig:
    """Configuration for inventory optimization."""

    method: str = "ppo"
    waste_cost_weight: float = 1.0
    stockout_cost_weight: float = 1.5
    holding_cost_per_unit: float = 0.1
    episode_length: int = 90
    total_timesteps: int = 100_000


@dataclass
class FederatedConfig:
    """Configuration for federated learning."""

    strategy: str = "fedavg"
    n_rounds: int = 50
    fraction_fit: float = 1.0
    local_epochs: int = 5
    mu: float = 0.1  # FedProx proximal term


@dataclass
class MeshekConfig:
    """Top-level project configuration composing all pillars."""

    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    demand: DemandConfig = field(default_factory=DemandConfig)
    forecasting: ForecastingConfig = field(default_factory=ForecastingConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    federated: FederatedConfig = field(default_factory=FederatedConfig)
