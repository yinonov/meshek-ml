# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**Managed external services:**
- None detected in the inspected repository. No HTTP client libraries, cloud SDKs, database drivers, or SaaS integrations were found in `src/` or `scripts/`.
- The project currently runs as a local Python package with file-based inputs and outputs rather than a service-oriented application.

**Planned but not yet wired service-style integration:**
- Flower (`flwr`) is the intended federated-learning framework, referenced in `pyproject.toml` and in stubs under `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, and `src/meshek_ml/federated/federated_xgboost.py`.
- Streamlit is the intended local UI runtime, launched by `scripts/run_demo.py` and targeting `src/meshek_ml/demo/dashboard.py`, but the dashboard file is still a stub.

## Libraries as Integration Boundaries

**Synthetic data generation:**
- `Faker` integrates localized fake-entity generation in `src/meshek_ml/simulation/merchants.py`, using `Faker("he_IL")` for merchant names and locations.
- `numpy`, `pandas`, and `scipy` form the numerical interface for generating daily demand, holiday effects, seasonality, spoilage, and analytical optimization in `src/meshek_ml/simulation/demand.py`, `src/meshek_ml/simulation/calendar.py`, `src/meshek_ml/simulation/spoilage.py`, and `src/meshek_ml/optimization/newsvendor.py`.

**Forecast-model adapters:**
- `prophet` is wrapped in `src/meshek_ml/forecasting/prophet_model.py`.
- `lightgbm` and `xgboost` are wrapped in `src/meshek_ml/forecasting/tree_models.py`.
- `darts` is wrapped in `src/meshek_ml/forecasting/darts_adapter.py` to convert between pandas DataFrames and Darts `TimeSeries` objects.
- These are lazy imports, so the repo can import the package without all forecasting extras installed.

**Reinforcement learning:**
- `gymnasium` defines the environment contract in `src/meshek_ml/optimization/env.py`.
- `stable_baselines3` provides PPO training and model serialization in `src/meshek_ml/optimization/ppo_agent.py`.
- `torch` is not a direct modeling API in most files, but `src/meshek_ml/common/seed.py` seeds it when available and the optimization/federated extras declare it as a dependency.

## Data Storage

**Databases:**
- None. No SQL, NoSQL, or embedded database integration was detected.

**Primary persistent storage:**
- Local filesystem under repository-relative paths.
- Synthetic data output is written to `data/synthetic/demand.parquet` by `scripts/run_simulation.py`.
- General CSV/parquet helpers are defined in `src/meshek_ml/common/io.py`.
- PPO model artifacts are saved to an arbitrary local path via `src/meshek_ml/optimization/ppo_agent.py`.

**File formats:**
- Parquet is the primary machine-readable dataset format, written by `src/meshek_ml/common/io.py` and validated in `tests/common/test_io.py`.
- CSV support exists in `src/meshek_ml/common/io.py`, but no checked-in operational script currently uses it.
- YAML is the configuration format across `configs/`.
- Notebook JSON is used for exploratory analysis in `notebooks/`.

**Caching:**
- No explicit application cache layer detected.
- `outputs/`, `multirun/`, and `.pytest_cache/` are treated as disposable generated directories by the `clean` target in `Makefile`.

## Configuration Interfaces

**Config directories:**
- Simulation: `configs/simulation/default.yaml`, `configs/simulation/merchant_archetypes.yaml`, `configs/simulation/seasonality.yaml`
- Forecasting: `configs/forecasting/lightgbm.yaml`, `configs/forecasting/prophet.yaml`
- Optimization: `configs/optimization/ppo.yaml`, `configs/optimization/newsvendor.yaml`
- Federated: `configs/federated/fedavg.yaml`, `configs/federated/fedprox.yaml`
- Experiment overrides: `configs/experiment/sim_small.yaml`

**Config schema layer:**
- `src/meshek_ml/common/config.py` defines dataclass-based structured config objects for simulation, demand, forecasting, optimization, and federated settings.

**Current integration status:**
- Config files are present and specific, but the runnable scripts do not yet consume them through Hydra or OmegaConf.
- `scripts/run_forecast.py`, `scripts/run_optimization.py`, and `scripts/run_federated.py` explicitly note TODOs for Hydra-based config loading.
- `scripts/run_simulation.py` currently hardcodes its runtime parameters instead of reading `configs/simulation/default.yaml`.

**Environment configuration:**
- No env-var contract was found in the inspected code or YAML files.
- No `.env` usage, secrets loader, or external credential lookup was detected.

## Model and Data Interfaces

**Core tabular contract:**
- Simulation produces pandas DataFrames with fields documented in `src/meshek_ml/simulation/generator.py` and `src/meshek_ml/simulation/demand.py`, including `date`, `merchant_id`, `product`, `base_demand`, `seasonal_factor`, `weekly_factor`, `holiday_factor`, `adjusted_demand`, and `realized_demand`.
- Federated partitioning expects the same tabular shape and splits by `merchant_id` in `src/meshek_ml/federated/partitioning.py`.

**Forecasting interfaces:**
- Prophet expects a training DataFrame with a date column and target column, then internally maps to Prophet's `ds` / `y` schema in `src/meshek_ml/forecasting/prophet_model.py`.
- Tree models expect `x_train: pd.DataFrame` and `y_train: np.ndarray` in `src/meshek_ml/forecasting/tree_models.py`.
- Darts integration converts DataFrames to and from `TimeSeries` objects in `src/meshek_ml/forecasting/darts_adapter.py`.
- The top-level forecasting orchestrator exists as `src/meshek_ml/forecasting/pipeline.py` but still raises `NotImplementedError`.

**Optimization interfaces:**
- `src/meshek_ml/optimization/env.py` exposes a standard Gymnasium `Env` with continuous order actions and vector observations.
- `src/meshek_ml/optimization/ppo_agent.py` accepts any Gymnasium-compatible environment and can save or load PPO artifacts from local disk.
- `src/meshek_ml/optimization/newsvendor.py` provides analytical functions over scalar demand and cost parameters rather than a persisted model interface.

## Notebooks and Human-Facing Interfaces

**Notebook integration points:**
- `notebooks/01_simulation_eda.ipynb` imports `meshek_ml.simulation.generator.run_simulation` and `meshek_ml.common.plotting.plot_demand_series` for local exploration.
- `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, and `notebooks/04_federated_learning.ipynb` define future workflow scopes but remain TODO notebooks.

**CLI / operator entry points:**
- `Makefile` is the main operator interface for install, lint, test, run, and cleanup commands.
- `scripts/run_simulation.py` is the only data-producing operational script currently implemented end to end.
- `scripts/run_demo.py` is a thin subprocess wrapper around Streamlit.

## Authentication & Identity

**Auth provider:**
- None.
- The codebase has no user accounts, API keys, session handling, or identity-provider integration.

## Monitoring & Observability

**Error tracking:**
- None detected.

**Logging:**
- Minimal console output only. `scripts/run_simulation.py` prints the record count and output path.
- No structured logging library, tracing, metrics emitter, or experiment tracker was found.

## CI/CD & Deployment

**Hosting:**
- Not applicable for current code paths. No deployment target is encoded in the repository.

**CI pipeline:**
- No CI workflow files or build-pipeline config were included in the inspected starting points.
- Local quality gates are `pytest` and `ruff` via `Makefile` and `pyproject.toml`.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None.

---

*Integration audit: 2026-03-24*
