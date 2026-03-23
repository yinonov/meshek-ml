# meshek-ml

Federated inventory optimization for perishable goods at small greengrocers.

## Overview

This project combines four ML pillars to help small produce merchants reduce waste and stockouts:

1. **Simulation** — Synthetic data generation with realistic demand patterns (Negative Binomial), Israeli holiday effects, weekly seasonality, and Weibull spoilage decay
2. **Demand Forecasting** — Prophet baseline, LightGBM/XGBoost with engineered features, evaluated on asymmetric (pinball) loss
3. **Inventory Optimization** — Newsvendor analytical baseline and PPO reinforcement learning agent with asymmetric cost functions
4. **Federated Learning** — Flower-based multi-merchant collaborative training (FedAvg/FedProx) without sharing raw sales data

## Quick Start

```bash
# Install core + simulation dependencies
pip install -e ".[dev,simulation]"

# Install everything
pip install -e ".[all]"

# Run simulation
make sim

# Run tests
make test

# Lint
make lint
```

## Project Structure

```
configs/          Hydra configuration files
data/             Raw, processed, and synthetic data
notebooks/        Jupyter exploration notebooks
scripts/          CLI entry points
src/meshek_ml/    Source code
  simulation/     Synthetic data generation
  forecasting/    Demand forecasting models
  optimization/   Inventory optimization (newsvendor + RL)
  federated/      Federated learning (Flower)
  common/         Shared utilities
  demo/           Streamlit dashboard
tests/            Test suite
```

## Development

```bash
# Format code
make format

# Run all tests (including slow)
make test-all

# Set up pre-commit hooks
pre-commit install
```
