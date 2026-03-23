"""Tests for the Gymnasium inventory environment."""

import numpy as np
import pytest

gymnasium = pytest.importorskip("gymnasium")


def test_env_reset_and_step():
    from meshek_ml.optimization.env import PerishableInventoryEnv

    env = PerishableInventoryEnv(max_shelf_life=5, episode_length=10)
    obs, info = env.reset(seed=42)
    assert obs.shape == env.observation_space.shape

    action = np.array([15.0], dtype=np.float32)
    obs, reward, _terminated, _truncated, info = env.step(action)
    assert obs.shape == env.observation_space.shape
    assert isinstance(reward, float)
    assert "sold" in info
    assert "wasted" in info
