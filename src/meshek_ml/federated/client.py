"""Flower client implementation for federated training."""

from __future__ import annotations

# Stub — requires flwr dependency
# Implementation will define a FlowerClient(flwr.client.NumPyClient)
# that handles local training on merchant data and parameter exchange.


def create_client_fn(merchant_data, model_factory):
    """Create a Flower client factory function.

    Args:
        merchant_data: Local merchant's training data.
        model_factory: Callable that creates a fresh model instance.

    Returns:
        A function that creates a FlowerClient when called.
    """
    # TODO: Implement with flwr.client.NumPyClient
    raise NotImplementedError("Flower client not yet implemented")
