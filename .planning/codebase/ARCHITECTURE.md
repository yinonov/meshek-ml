# Architecture

**Analysis Date:** 2026-03-24

## Pattern Overview

**Overall:** Domain-oriented Python research pipeline with thin CLI wrappers, notebook-driven exploration, and a shared package under `src/meshek_ml/`.

**Key Characteristics:**
- Treat `src/meshek_ml/simulation/` as the source-of-truth data generator that feeds the rest of the project.
- Pass tabular state between pillars as `pandas.DataFrame` objects rather than through a service layer or persisted domain objects.
- Keep orchestration shallow: `scripts/run_simulation.py` and `scripts/run_demo.py` are executable entry points, while several other scripts currently delegate users to package modules or placeholders.
- Use package boundaries by problem domain: `simulation`, `forecasting`, `optimization`, `federated`, `demo`, and `common`.
- Keep configuration split between YAML files in `configs/` and structured dataclasses in `src/meshek_ml/common/config.py`, with only partial runtime wiring today.

## Mental Model

Think about the project as a staged workflow:
1. Generate synthetic merchant-by-product demand histories in `src/meshek_ml/simulation/generator.py`.
2. Persist or reload those datasets through `src/meshek_ml/common/io.py` and files under `data/synthetic/`.
3. Feed the resulting merchant/product time series into forecasting utilities in `src/meshek_ml/forecasting/`.
4. Use forecast assumptions or direct demand distributions to evaluate ordering policies in `src/meshek_ml/optimization/`.
5. Split merchant-level data with `src/meshek_ml/federated/partitioning.py` for federated experiments once the Flower client/server stubs are implemented.
6. Surface experiments interactively through `notebooks/` and eventually `src/meshek_ml/demo/dashboard.py`.

## Layers

**Project Entry Layer:**
- Purpose: Human-invoked entry points for development, experiments, and demos.
- Location: `Makefile`, `scripts/run_simulation.py`, `scripts/run_forecast.py`, `scripts/run_optimization.py`, `scripts/run_federated.py`, `scripts/run_demo.py`, `notebooks/01_simulation_eda.ipynb`, `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, `notebooks/04_federated_learning.ipynb`.
- Contains: Make targets, small `main()` wrappers, and exploratory notebook cells.
- Depends on: `src/meshek_ml/` package modules, `streamlit`, and the local Python environment.
- Used by: Developers running `make sim`, `make demo`, `pytest`, or notebook sessions.

**Configuration Layer:**
- Purpose: Declare experiment defaults and intended runtime knobs across pillars.
- Location: `configs/simulation/default.yaml`, `configs/forecasting/lightgbm.yaml`, `configs/optimization/ppo.yaml`, `configs/federated/fedavg.yaml`, and `src/meshek_ml/common/config.py`.
- Contains: YAML parameter sets and dataclass-based structured configs (`SimulationConfig`, `ForecastingConfig`, `OptimizationConfig`, `FederatedConfig`, `MeshekConfig`).
- Depends on: `dataclasses`; no active Hydra entry-point wiring is present in the scripts yet.
- Used by: Future orchestration code and planning documents; current executable scripts do not yet consume the YAML files.

**Simulation Layer:**
- Purpose: Generate realistic synthetic data for merchants, products, demand, seasonality, and spoilage.
- Location: `src/meshek_ml/simulation/`.
- Contains: Catalog definitions in `src/meshek_ml/simulation/generator.py`, merchant synthesis in `src/meshek_ml/simulation/merchants.py`, demand generation in `src/meshek_ml/simulation/demand.py`, calendar effects in `src/meshek_ml/simulation/calendar.py`, spoilage/inventory mechanics in `src/meshek_ml/simulation/spoilage.py`, and typed schemas in `src/meshek_ml/simulation/schemas.py`.
- Depends on: `src/meshek_ml/common/types.py`, `numpy`, `pandas`, `scipy`, and `faker`.
- Used by: `scripts/run_simulation.py`, `notebooks/01_simulation_eda.ipynb`, and downstream forecasting/optimization/federated workflows.

**Forecasting Layer:**
- Purpose: Build features, fit forecasting models, and evaluate predictions on simulated or future demand data.
- Location: `src/meshek_ml/forecasting/`.
- Contains: Feature engineering in `src/meshek_ml/forecasting/features.py`, model wrappers in `src/meshek_ml/forecasting/tree_models.py` and `src/meshek_ml/forecasting/prophet_model.py`, conversion helpers in `src/meshek_ml/forecasting/darts_adapter.py`, metrics in `src/meshek_ml/forecasting/evaluation.py`, and intended orchestration in `src/meshek_ml/forecasting/pipeline.py`.
- Depends on: `pandas` data produced by the simulation layer, plus optional ML libraries such as LightGBM, XGBoost, Prophet/Darts.
- Used by: `notebooks/02_demand_forecasting.ipynb`; `scripts/run_forecast.py` is still a placeholder and points users back to this package.

**Optimization Layer:**
- Purpose: Compare analytical and reinforcement-learning inventory decisions for perishables.
- Location: `src/meshek_ml/optimization/`.
- Contains: Newsvendor baselines in `src/meshek_ml/optimization/newsvendor.py`, environment dynamics in `src/meshek_ml/optimization/env.py`, reward calculation in `src/meshek_ml/optimization/rewards.py`, PPO training in `src/meshek_ml/optimization/ppo_agent.py`, and metrics in `src/meshek_ml/optimization/evaluation.py`.
- Depends on: `src/meshek_ml/simulation/spoilage.py` for `FIFOInventory`, `gymnasium`, `numpy`, `scipy`, and optional `stable_baselines3`.
- Used by: `notebooks/03_inventory_optimization.ipynb`; `scripts/run_optimization.py` is currently a placeholder.

**Federated Layer:**
- Purpose: Partition merchant data and eventually orchestrate collaborative training without sharing raw data.
- Location: `src/meshek_ml/federated/`.
- Contains: Data partitioning in `src/meshek_ml/federated/partitioning.py`, placeholder client/server/strategy modules in `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, plus personalization helpers in `src/meshek_ml/federated/personalization.py` and tree aggregation work in `src/meshek_ml/federated/federated_xgboost.py`.
- Depends on: Merchant-keyed data from simulation or forecasting outputs and optional `flwr`.
- Used by: `notebooks/04_federated_learning.ipynb`; `scripts/run_federated.py` currently only announces that implementation is pending.

**Shared Utilities Layer:**
- Purpose: Hold low-level helpers reused by multiple pillars.
- Location: `src/meshek_ml/common/`.
- Contains: File IO in `src/meshek_ml/common/io.py`, seed control in `src/meshek_ml/common/seed.py`, enums and metric aliases in `src/meshek_ml/common/types.py`, plotting in `src/meshek_ml/common/plotting.py`, and config dataclasses in `src/meshek_ml/common/config.py`.
- Depends on: Standard scientific Python stack.
- Used by: Nearly every package, especially simulation scripts and notebooks.

**Presentation Layer:**
- Purpose: Interactive demonstration surface for non-code exploration.
- Location: `src/meshek_ml/demo/dashboard.py` and `src/meshek_ml/demo/scenarios.py`.
- Contains: Streamlit dashboard and scenario stubs.
- Depends on: All domain pillars once implemented.
- Used by: `scripts/run_demo.py` and `make demo`.

## Data Flow

**Synthetic Data to Forecasting/Optimization Flow:**

1. `scripts/run_simulation.py` seeds randomness with `src/meshek_ml/common/seed.py` and calls `run_simulation()` in `src/meshek_ml/simulation/generator.py`.
2. `run_simulation()` creates merchant profiles with `src/meshek_ml/simulation/merchants.py`, iterates a default product catalog, and calls `generate_demand()` in `src/meshek_ml/simulation/demand.py` for each merchant/product pair.
3. Simulation returns one concatenated `pandas.DataFrame` with columns such as `date`, `merchant_id`, `product`, `adjusted_demand`, and `realized_demand`.
4. `src/meshek_ml/common/io.py` writes the dataset to `data/synthetic/demand.parquet` or reloads it for later experiments.
5. Forecasting code in `src/meshek_ml/forecasting/features.py` expects the same tabular shape and adds lag, rolling, and calendar features grouped by `merchant_id` and `product`.
6. Optimization code either consumes direct distribution assumptions (`src/meshek_ml/optimization/newsvendor.py`) or simulates daily inventory control inside `src/meshek_ml/optimization/env.py`.

**Federated Experiment Flow:**

1. Start from a full merchant-level dataset created by simulation or future forecasting outputs.
2. Split the full dataset into local merchant silos with `partition_by_merchant()` in `src/meshek_ml/federated/partitioning.py`.
3. Hand each partition to a Flower client factory in `src/meshek_ml/federated/client.py` once that stub is implemented.
4. Aggregate client updates through `src/meshek_ml/federated/server.py` and `src/meshek_ml/federated/strategies.py`.

**State Management:**
- Runtime state is mostly in-memory Python objects and `pandas.DataFrame` values.
- Persistence is file-based through `data/`, `models/`, `outputs/`, and `reports/` rather than a database.
- There is no application container or service registry; composition happens through direct imports and function calls.

## Key Abstractions

**Structured Domain Specs:**
- Purpose: Represent products, merchants, and record shapes explicitly.
- Examples: `src/meshek_ml/simulation/schemas.py`, `src/meshek_ml/common/types.py`.
- Pattern: Lightweight dataclasses and enums instead of ORM models or service entities.

**Tabular Handoff Contract:**
- Purpose: Provide a simple interchange format between simulation, forecasting, and federated partitioning.
- Examples: `src/meshek_ml/simulation/generator.py`, `src/meshek_ml/forecasting/features.py`, `src/meshek_ml/federated/partitioning.py`, `src/meshek_ml/common/io.py`.
- Pattern: Functions accept and return `pandas.DataFrame` objects with merchant/product/date columns.

**Perishable Inventory Engine:**
- Purpose: Model spoilage and stock consumption over time.
- Examples: `src/meshek_ml/simulation/spoilage.py`, `src/meshek_ml/optimization/env.py`.
- Pattern: `FIFOInventory` is a reusable state machine embedded inside the RL environment rather than duplicated there.

**Experiment Config Surface:**
- Purpose: Capture intended defaults for each ML pillar.
- Examples: `src/meshek_ml/common/config.py`, `configs/simulation/default.yaml`, `configs/forecasting/lightgbm.yaml`, `configs/optimization/ppo.yaml`, `configs/federated/fedavg.yaml`.
- Pattern: Dataclasses for typed defaults plus YAML for scenario presets; runtime binding is incomplete.

## Entry Points

**Simulation CLI:**
- Location: `scripts/run_simulation.py`
- Triggers: `python scripts/run_simulation.py` or `make sim`.
- Responsibilities: Seed the process, generate synthetic data, and write `data/synthetic/demand.parquet`.

**Demo CLI:**
- Location: `scripts/run_demo.py`
- Triggers: `python scripts/run_demo.py` or `make demo`.
- Responsibilities: Launch Streamlit with `src/meshek_ml/demo/dashboard.py`.

**Placeholder CLIs:**
- Location: `scripts/run_forecast.py`, `scripts/run_optimization.py`, `scripts/run_federated.py`
- Triggers: `make forecast`, `make optimize`, `make federate`.
- Responsibilities: Reserve top-level commands and point users to package modules; these scripts do not yet execute the intended pipelines.

**Notebook Entry Points:**
- Location: `notebooks/01_simulation_eda.ipynb`, `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, `notebooks/04_federated_learning.ipynb`
- Triggers: Manual Jupyter execution.
- Responsibilities: Provide exploratory, pillar-specific workflows; only `notebooks/01_simulation_eda.ipynb` currently contains executable package usage beyond TODO placeholders.

## Error Handling

**Strategy:** Fail fast with standard Python exceptions and explicit `NotImplementedError` for unfinished pillars.

**Patterns:**
- Use `raise NotImplementedError(...)` to mark incomplete orchestration in `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/federated/client.py`, and `src/meshek_ml/federated/server.py`.
- Rely on library exceptions from `pandas`, `numpy`, `gymnasium`, and model libraries instead of wrapping them in custom error types.
- Use `subprocess.run(..., check=True)` in `scripts/run_demo.py` so the process fails immediately if Streamlit cannot start.

## Cross-Cutting Concerns

**Logging:** Minimal. Current scripts use `print()` in `scripts/run_simulation.py` and placeholder text in CLI stubs; there is no centralized logging layer.
**Validation:** Mostly type-level and structural. Dataclasses in `src/meshek_ml/simulation/schemas.py` and `src/meshek_ml/common/config.py` define expected fields, but runtime validation is limited.
**Authentication:** Not applicable. The repository is a local experiment/workbench and does not expose authenticated services.

---

*Architecture analysis: 2026-03-24*
