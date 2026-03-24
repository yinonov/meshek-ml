# Codebase Structure

**Analysis Date:** 2026-03-24

## Directory Layout

```text
meshek-ml/
├── configs/                 # YAML presets by pillar and experiment
├── data/                    # Raw, processed, and synthetic datasets
├── models/                  # Saved trained models and checkpoints
├── notebooks/               # Pillar-specific exploratory notebooks
├── outputs/                 # Run artifacts and generated experiment output
├── reports/                 # Human-facing figures and reporting assets
├── scripts/                 # Thin CLI entry points
├── src/meshek_ml/           # Installable Python package
├── tests/                   # Test suite mirroring source domains
├── Makefile                 # Common developer commands
├── pyproject.toml           # Packaging, dependencies, pytest, ruff
└── README.md                # Project overview and quick start
```

## Directory Purposes

**`configs/`:**
- Purpose: Store YAML parameter sets for simulation, forecasting, optimization, federated learning, and experiments.
- Contains: `configs/simulation/default.yaml`, `configs/forecasting/lightgbm.yaml`, `configs/forecasting/prophet.yaml`, `configs/optimization/ppo.yaml`, `configs/optimization/newsvendor.yaml`, `configs/federated/fedavg.yaml`, `configs/federated/fedprox.yaml`, `configs/experiment/sim_small.yaml`.
- Key files: `configs/simulation/default.yaml`, `configs/forecasting/lightgbm.yaml`, `configs/optimization/ppo.yaml`, `configs/federated/fedavg.yaml`.

**`data/`:**
- Purpose: Hold input and generated datasets outside the package code.
- Contains: `data/raw/`, `data/processed/`, `data/synthetic/`.
- Key files: `data/synthetic/demand.parquet` is the path written by `scripts/run_simulation.py` when simulation runs.

**`notebooks/`:**
- Purpose: Provide exploratory or demo-oriented analysis per project pillar.
- Contains: `notebooks/01_simulation_eda.ipynb`, `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, `notebooks/04_federated_learning.ipynb`.
- Key files: `notebooks/01_simulation_eda.ipynb` is the most concrete notebook today; later notebooks are scaffold notebooks with TODO code cells.

**`scripts/`:**
- Purpose: Keep command-line entry points thin and human-friendly.
- Contains: `scripts/run_simulation.py`, `scripts/run_forecast.py`, `scripts/run_optimization.py`, `scripts/run_federated.py`, `scripts/run_demo.py`.
- Key files: `scripts/run_simulation.py` and `scripts/run_demo.py` are functional; the other three scripts are placeholders that defer to package code.

**`src/meshek_ml/`:**
- Purpose: Hold all reusable application logic in an installable package.
- Contains: Domain packages `common`, `simulation`, `forecasting`, `optimization`, `federated`, and `demo`.
- Key files: `src/meshek_ml/common/config.py`, `src/meshek_ml/simulation/generator.py`, `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/optimization/env.py`, `src/meshek_ml/federated/partitioning.py`, `src/meshek_ml/demo/dashboard.py`.

**`tests/`:**
- Purpose: Mirror source-domain coverage with pytest tests.
- Contains: `tests/common/`, `tests/simulation/`, `tests/forecasting/`, `tests/optimization/`, `tests/federated/`.
- Key files: `tests/simulation/test_generator.py`, `tests/forecasting/test_features.py`, `tests/optimization/test_env.py`, `tests/federated/test_partitioning.py`.

**`reports/`:**
- Purpose: Store generated visuals and reporting artifacts.
- Contains: `reports/figures/`.
- Key files: No committed figure files were surfaced during this pass; treat the directory as an output target.

**`models/`:**
- Purpose: Store trained model artifacts.
- Contains: Model files created by training code such as `src/meshek_ml/optimization/ppo_agent.py` when `save_path` is provided.
- Key files: No committed model artifacts were surfaced during this pass.

**`outputs/`:**
- Purpose: Hold experiment run outputs or Hydra-style run directories.
- Contains: Repository-local generated output.
- Key files: None surfaced during this pass; treat this as disposable run output.

## Key File Locations

**Entry Points:**
- `README.md`: Project overview, quick start, and high-level pillar description.
- `Makefile`: Canonical developer commands for install, lint, test, simulation, and demo.
- `scripts/run_simulation.py`: Main executable simulation workflow.
- `scripts/run_demo.py`: Streamlit launcher.
- `notebooks/01_simulation_eda.ipynb`: Concrete exploratory workflow.

**Configuration:**
- `pyproject.toml`: Packaging metadata, optional dependencies, pytest configuration, and Ruff rules.
- `src/meshek_ml/common/config.py`: Structured config dataclasses spanning all pillars.
- `configs/simulation/default.yaml`: Simulation defaults.
- `configs/forecasting/lightgbm.yaml`: Forecasting model and feature defaults.
- `configs/optimization/ppo.yaml`: RL environment and training defaults.
- `configs/federated/fedavg.yaml`: Federated strategy defaults.

**Core Logic:**
- `src/meshek_ml/simulation/generator.py`: End-to-end synthetic dataset builder.
- `src/meshek_ml/simulation/demand.py`: Demand generation math and output columns.
- `src/meshek_ml/simulation/spoilage.py`: Inventory aging and FIFO sell-through.
- `src/meshek_ml/forecasting/features.py`: Tabular feature engineering.
- `src/meshek_ml/forecasting/tree_models.py`: Gradient boosting model wrappers.
- `src/meshek_ml/optimization/env.py`: RL environment for perishable inventory.
- `src/meshek_ml/optimization/newsvendor.py`: Analytical ordering baselines.
- `src/meshek_ml/federated/partitioning.py`: Merchant and IID dataset splits.

**Testing:**
- `tests/conftest.py`: Shared pytest fixtures and configuration.
- `tests/simulation/test_generator.py`: Simulation orchestration coverage.
- `tests/forecasting/test_features.py`: Feature engineering coverage.
- `tests/optimization/test_env.py`: Environment behavior coverage.
- `tests/federated/test_partitioning.py`: Federated split correctness coverage.

## Naming Conventions

**Files:**
- Use lowercase snake_case Python modules such as `generator.py`, `tree_models.py`, `ppo_agent.py`, and `test_generator.py`.
- Use numbered notebook filenames to reflect the intended user journey: `01_simulation_eda.ipynb` through `04_federated_learning.ipynb`.
- Use YAML filenames that encode scenario or algorithm names such as `fedavg.yaml`, `lightgbm.yaml`, and `merchant_archetypes.yaml`.

**Directories:**
- Group by domain capability under `src/meshek_ml/` rather than by technical layer. Add simulation code to `src/meshek_ml/simulation/`, forecasting code to `src/meshek_ml/forecasting/`, and so on.
- Mirror those domain groupings under `tests/` and `configs/` whenever the new work needs tests or parameter presets.

## Module Grouping

**`src/meshek_ml/common/`:**
- Shared helpers only. Put cross-pillar utilities here if they are generic enough to be imported by multiple domain packages.
- Keep domain-specific logic out of `common`; for example, spoilage stays in `src/meshek_ml/simulation/spoilage.py` even though optimization reuses it.

**`src/meshek_ml/simulation/`:**
- Split by domain concept: schemas in `schemas.py`, merchant synthesis in `merchants.py`, temporal effects in `calendar.py`, spoilage in `spoilage.py`, and orchestration in `generator.py`.
- New simulation features should usually follow this same pattern rather than expanding `generator.py` into a monolith.

**`src/meshek_ml/forecasting/`:**
- Keep feature engineering, model wrappers, evaluation, and orchestration separate.
- New model backends should typically get their own module alongside `prophet_model.py` and `tree_models.py`, then be wired into `pipeline.py`.

**`src/meshek_ml/optimization/`:**
- Separate policy math (`newsvendor.py`), environment dynamics (`env.py`), reward definitions (`rewards.py`), training wrappers (`ppo_agent.py`), and metrics (`evaluation.py`).
- Additional agents or optimization approaches should land in new sibling modules inside this package.

**`src/meshek_ml/federated/`:**
- Keep data partitioning, client logic, server logic, strategies, and personalization separate.
- Future Flower implementations should fill in the existing modules instead of creating parallel orchestration paths elsewhere.

**`src/meshek_ml/demo/`:**
- Reserve for user-facing Streamlit code and reusable demo scenarios.
- Keep shell launching in `scripts/run_demo.py`; keep UI logic in `src/meshek_ml/demo/dashboard.py`.

## Where to Add New Code

**New Simulation Capability:**
- Primary code: `src/meshek_ml/simulation/`.
- Config: `configs/simulation/`.
- Tests: `tests/simulation/`.
- Notebook exploration: `notebooks/01_simulation_eda.ipynb` or a new numbered notebook if the workflow deserves its own narrative.

**New Forecasting Model or Pipeline Step:**
- Primary code: `src/meshek_ml/forecasting/`.
- Config: `configs/forecasting/`.
- Tests: `tests/forecasting/`.
- CLI wiring: update `src/meshek_ml/forecasting/pipeline.py` first, then make `scripts/run_forecast.py` a thin wrapper around it.

**New Inventory Optimization Method:**
- Primary code: `src/meshek_ml/optimization/`.
- Config: `configs/optimization/`.
- Tests: `tests/optimization/`.
- Artifacts: save trained outputs under `models/` or `outputs/`, not under `src/`.

**New Federated Workflow:**
- Primary code: `src/meshek_ml/federated/`.
- Config: `configs/federated/`.
- Tests: `tests/federated/`.
- Dataset prep: keep merchant partition creation in `src/meshek_ml/federated/partitioning.py` or adjacent helpers.

**New Shared Helper:**
- Shared helpers: `src/meshek_ml/common/`.
- Rule: only place code here if at least two pillar packages need it; otherwise keep it local to the pillar package.

**New CLI or Automation Command:**
- Thin command wrapper: `scripts/`.
- Common invocation shortcut: `Makefile`.
- Rule: business logic belongs in `src/meshek_ml/`, not in script files.

## Special Directories

**`.planning/codebase/`:**
- Purpose: Generated planning references for future GSD phases.
- Generated: Yes.
- Committed: Intended to be committed when kept as project planning context.

**`.venv/`:**
- Purpose: Local Python virtual environment.
- Generated: Yes.
- Committed: No.

**`.pytest_cache/` and `.ruff_cache/`:**
- Purpose: Local tool caches.
- Generated: Yes.
- Committed: No.

**`reports/figures/`:**
- Purpose: Persist generated figures separate from raw notebooks.
- Generated: Yes.
- Committed: Project-dependent, but structurally intended for durable outputs.

---

*Structure analysis: 2026-03-24*
