# Technology Stack

**Analysis Date:** 2026-03-24

## Languages

**Primary:**
- Python 3.9+ - application code, scripts, tests, and notebooks under `src/meshek_ml/`, `scripts/`, `tests/`, and `notebooks/`.
- YAML - runtime configuration surfaces under `configs/simulation/`, `configs/forecasting/`, `configs/optimization/`, `configs/federated/`, and `configs/experiment/`.

**Secondary:**
- Markdown - operator and developer guidance in `README.md`.
- Jupyter Notebook JSON - exploratory workflows in `notebooks/01_simulation_eda.ipynb`, `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, and `notebooks/04_federated_learning.ipynb`.

## Runtime

**Environment:**
- CPython >=3.9, declared in `pyproject.toml`.
- Editable-package workflow via `pip install -e ...`, driven by `Makefile` targets and `README.md` commands.

**Package Manager:**
- `pip` installs the project extras shown in `Makefile` and `README.md`.
- Build backend: `hatchling`, configured in `pyproject.toml`.
- Lockfile: missing. No `uv.lock`, `poetry.lock`, `Pipfile.lock`, or `requirements.txt` detected.

## Frameworks

**Core:**
- `pandas`, `numpy`, and `scipy` are the active numerical/data stack. They are used directly in `src/meshek_ml/simulation/generator.py`, `src/meshek_ml/simulation/demand.py`, `src/meshek_ml/simulation/calendar.py`, `src/meshek_ml/simulation/spoilage.py`, `src/meshek_ml/forecasting/features.py`, `src/meshek_ml/forecasting/evaluation.py`, `src/meshek_ml/optimization/env.py`, and `src/meshek_ml/optimization/newsvendor.py`.
- Dataclass-based structured config objects live in `src/meshek_ml/common/config.py`.
- Local persistence helpers live in `src/meshek_ml/common/io.py`.

**ML / Modeling:**
- Forecasting wrappers target `prophet`, `lightgbm`, `xgboost`, and `darts` in `src/meshek_ml/forecasting/prophet_model.py`, `src/meshek_ml/forecasting/tree_models.py`, and `src/meshek_ml/forecasting/darts_adapter.py`.
- Inventory optimization uses `gymnasium` in `src/meshek_ml/optimization/env.py` and `stable_baselines3` in `src/meshek_ml/optimization/ppo_agent.py`.
- Reproducibility optionally seeds `torch` in `src/meshek_ml/common/seed.py`.
- Federated learning is planned around `flwr`, but the executable pieces are still placeholders or stubs in `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, `src/meshek_ml/federated/federated_xgboost.py`, and `scripts/run_federated.py`.

**Visualization / Demo:**
- `matplotlib` powers plots in `src/meshek_ml/common/plotting.py`.
- `streamlit` is the intended UI runtime for `src/meshek_ml/demo/dashboard.py`, launched by `scripts/run_demo.py` or `make demo`.
- `seaborn` is declared in `pyproject.toml` but no active import was found in `src/` or `scripts/`.

**Development / Test:**
- `pytest` and `pytest-cov` are configured in `pyproject.toml` and invoked by `Makefile` targets `test` and `test-all`.
- `ruff` is the formatter/linter, configured in `pyproject.toml` and invoked by `Makefile` targets `lint` and `format`.
- `pre-commit`, `ipykernel`, and `nbstripout` are development extras declared in `pyproject.toml`.

## Key Dependencies

**Critical runtime dependencies used by code:**
- `numpy>=1.24` - random generation, arrays, and metrics throughout `src/meshek_ml/simulation/`, `src/meshek_ml/forecasting/`, and `src/meshek_ml/optimization/`.
- `pandas>=2.0` - main tabular interface for simulation output, forecasting inputs, and partitioning in `src/meshek_ml/common/io.py`, `src/meshek_ml/simulation/generator.py`, and `src/meshek_ml/federated/partitioning.py`.
- `scipy>=1.11` - distribution math in `src/meshek_ml/simulation/spoilage.py` and `src/meshek_ml/optimization/newsvendor.py`.
- `pyarrow>=14.0` - implied by parquet round-trips in `src/meshek_ml/common/io.py` and validated in `tests/common/test_io.py`.
- `Faker>=20.0` - Hebrew-localized merchant generation in `src/meshek_ml/simulation/merchants.py`.

**Feature-gated optional dependencies:**
- `prophet` is imported lazily inside `src/meshek_ml/forecasting/prophet_model.py`.
- `lightgbm` and `xgboost` are imported lazily inside `src/meshek_ml/forecasting/tree_models.py`.
- `u8darts[all]` is imported lazily inside `src/meshek_ml/forecasting/darts_adapter.py`.
- `gymnasium`, `stable_baselines3`, and `torch` back the optimization path in `src/meshek_ml/optimization/env.py`, `src/meshek_ml/optimization/ppo_agent.py`, and `src/meshek_ml/common/seed.py`.
- `flwr` is declared for federated learning, but the repo currently exposes planning scaffolds more than a working runtime.
- `streamlit` is only required for the demo path in `scripts/run_demo.py` and `src/meshek_ml/demo/dashboard.py`.

**Declared but not operationally wired from inspected code:**
- `hydra-core` and `omegaconf` are declared in `pyproject.toml`, and `src/meshek_ml/common/config.py` defines dataclass configs, but no `@hydra.main` entry point or active OmegaConf loading was found in `scripts/` or `src/`.
- `pydantic` is declared in `pyproject.toml`, but no import was found in the inspected Python sources.

## Configuration

**Configuration surfaces actually present:**
- Simulation defaults: `configs/simulation/default.yaml`.
- Simulation smoke-test override: `configs/experiment/sim_small.yaml`.
- Forecasting model configs: `configs/forecasting/lightgbm.yaml` and `configs/forecasting/prophet.yaml`.
- Optimization configs: `configs/optimization/ppo.yaml` and `configs/optimization/newsvendor.yaml`.
- Federated configs: `configs/federated/fedavg.yaml` and `configs/federated/fedprox.yaml`.
- Structured config dataclasses: `src/meshek_ml/common/config.py`.

**Operational notes about config:**
- The YAML files define parameters and output locations, but the runnable scripts in `scripts/run_forecast.py`, `scripts/run_optimization.py`, and `scripts/run_federated.py` still print TODO placeholders instead of loading them.
- The only end-to-end operational script today is `scripts/run_simulation.py`, which bypasses Hydra and writes directly to `data/synthetic/demand.parquet`.
- No environment-variable reads or `.env`-driven runtime configuration were detected in the inspected code paths.

## Notebooks and Scripts

**Scripts:**
- `scripts/run_simulation.py` seeds RNGs, runs `meshek_ml.simulation.generator.run_simulation`, and saves parquet output to `data/synthetic/demand.parquet`.
- `scripts/run_demo.py` launches Streamlit against `src/meshek_ml/demo/dashboard.py`.
- `scripts/run_forecast.py`, `scripts/run_optimization.py`, and `scripts/run_federated.py` are command placeholders that currently route users to package modules rather than executing pipelines.

**Notebooks:**
- `notebooks/01_simulation_eda.ipynb` is the most concrete notebook; it imports `run_simulation` and `plot_demand_series` and performs EDA on synthetic demand.
- `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, and `notebooks/04_federated_learning.ipynb` currently carry titled TODO scaffolds for their respective workflows.

## Operational Entry Points

**Make targets:**
- `make sim` -> `python scripts/run_simulation.py`
- `make forecast` -> `python scripts/run_forecast.py`
- `make optimize` -> `python scripts/run_optimization.py`
- `make federate` -> `python scripts/run_federated.py`
- `make demo` -> `streamlit run src/meshek_ml/demo/dashboard.py`
- `make test` / `make test-all` / `make lint` / `make format` for validation and maintenance

**Primary package entry points by capability:**
- Simulation core: `src/meshek_ml/simulation/generator.py`
- Forecasting core: `src/meshek_ml/forecasting/pipeline.py` plus model adapters under `src/meshek_ml/forecasting/`
- Optimization core: `src/meshek_ml/optimization/env.py`, `src/meshek_ml/optimization/newsvendor.py`, and `src/meshek_ml/optimization/ppo_agent.py`
- Federated data partitioning: `src/meshek_ml/federated/partitioning.py`
- Demo UI stub: `src/meshek_ml/demo/dashboard.py`

## Platform Requirements

**Development:**
- Python 3.9+ with optional extras selected per workflow in `pyproject.toml`.
- Parquet support through `pyarrow`, exercised by `tests/common/test_io.py`.
- Jupyter kernel support for notebooks via the `dev` extra.

**Production / execution shape:**
- Local, file-backed execution. Current code writes artifacts to repository-relative directories such as `data/synthetic/`, `outputs/`, and `multirun/`.
- No container config, deployment manifest, web API server, or managed service runtime was detected in the inspected repository.

---

*Stack analysis: 2026-03-24*
