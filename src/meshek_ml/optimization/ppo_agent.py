"""PPO agent wrapper using Stable-Baselines3."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gymnasium import Env


def train_ppo(
    env: Env,
    total_timesteps: int = 100_000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    save_path: str | Path | None = None,
):
    """Train a PPO agent on the inventory environment.

    Args:
        env: Gymnasium environment (e.g., PerishableInventoryEnv).
        total_timesteps: Total training steps.
        learning_rate: PPO learning rate.
        n_steps: Steps per rollout buffer collection.
        save_path: Path to save the trained model.

    Returns:
        Trained PPO model.
    """
    from stable_baselines3 import PPO

    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        verbose=1,
    )
    model.learn(total_timesteps=total_timesteps)

    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(save_path))

    return model


def load_ppo(path: str | Path):
    """Load a saved PPO model.

    Args:
        path: Path to the saved model.

    Returns:
        Loaded PPO model.
    """
    from stable_baselines3 import PPO

    return PPO.load(str(path))
