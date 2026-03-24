# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- Use lowercase snake_case module names throughout `src/meshek_ml/`, for example `src/meshek_ml/simulation/generator.py`, `src/meshek_ml/forecasting/features.py`, and `src/meshek_ml/optimization/newsvendor.py`.
- Tests mirror the source package with the same snake_case plus a `test_` prefix, for example `tests/simulation/test_generator.py` and `tests/forecasting/test_features.py`.
- Script entry points in `scripts/` use `run_<area>.py`, for example `scripts/run_simulation.py` and `scripts/run_optimization.py`.

**Functions:**
- Use snake_case for public helpers and orchestrators, for example `set_global_seed`, `run_simulation`, `generate_demand`, `compute_all_metrics`, and `partition_by_merchant`.
- Test functions use behavior-oriented `test_<expected_behavior>` names rather than class-based suites, for example `test_generate_merchants_unique_ids` in `tests/simulation/test_merchants.py`.

**Variables:**
- Use descriptive snake_case names for domain values and intermediate arrays, for example `merchant_scale`, `weekly_factor`, `remaining_demand`, `total_actual`, and `current_day_of_week`.
- Short names are limited to math or loop-local contexts, for example `n`, `p`, `w`, and `i` in `src/meshek_ml/simulation/demand.py`, `src/meshek_ml/optimization/newsvendor.py`, and `src/meshek_ml/forecasting/features.py`.

**Types:**
- Domain enums use PascalCase classes with uppercase members in `src/meshek_ml/common/types.py`.
- Dataclasses use PascalCase nouns in `src/meshek_ml/common/config.py`, `src/meshek_ml/simulation/schemas.py`, and `src/meshek_ml/optimization/rewards.py`.
- Type aliases stay simple and local, for example `MetricsDict = dict[str, float]` in `src/meshek_ml/common/types.py`.

## Typing Patterns

- The codebase targets modern Python typing syntax with built-in generics and `|` unions, enabled by `from __future__ import annotations` in almost every source file under `src/meshek_ml/`.
- Function signatures are usually fully annotated, especially in pure computation modules such as `src/meshek_ml/forecasting/evaluation.py`, `src/meshek_ml/simulation/demand.py`, and `src/meshek_ml/optimization/rewards.py`.
- Pandas and NumPy types are annotated directly with `pd.DataFrame`, `pd.DatetimeIndex`, and `np.ndarray` in `src/meshek_ml/common/io.py`, `src/meshek_ml/forecasting/features.py`, and `src/meshek_ml/simulation/spoilage.py`.
- Dataclasses are the preferred schema and config mechanism. Use them instead of ad hoc dictionaries when representing structured domain state, following `SimulationConfig` in `src/meshek_ml/common/config.py`, `ProductSpec` in `src/meshek_ml/simulation/schemas.py`, and `CostParams` in `src/meshek_ml/optimization/rewards.py`.
- `Any` is used sparingly and only where required by third-party APIs, for example Gym reset options in `src/meshek_ml/optimization/env.py`.
- No static type checker configuration is present in `pyproject.toml`; typing is a code convention rather than an enforced CI gate.

## Code Style And Config

**Formatting:**
- The explicit style tool is Ruff in `pyproject.toml` with `line-length = "100"` behavior implied by `line-length = 100` and `target-version = "py39"`.
- Imports are expected to stay sorted via Ruff isort settings, with `meshek_ml` declared as first-party in `pyproject.toml`.
- Source files favor short module docstrings at the top of each file, for example `src/meshek_ml/common/seed.py` and `src/meshek_ml/simulation/generator.py`.

**Linting:**
- Ruff rules include `E`, `F`, `W`, `I`, `N`, `UP`, `B`, `SIM`, and `RUF` in `pyproject.toml`, so future code should match pycodestyle, naming, import-order, upgrade, bugbear, simplification, and Ruff-specific checks.
- No separate Black, mypy, or pylint configuration is detected.

**Config Patterns:**
- Project configuration is centralized in `pyproject.toml` for packaging, pytest, and linting.
- Runtime configuration is represented as structured dataclasses in `src/meshek_ml/common/config.py`; new configurable pipelines should extend `MeshekConfig` instead of scattering constants across modules.
- Optional dependencies are organized by project area in `[project.optional-dependencies]` inside `pyproject.toml`, and source files sometimes defer those imports until runtime, for example `faker` inside `generate_merchants` in `src/meshek_ml/simulation/merchants.py` and `torch` inside `set_global_seed` in `src/meshek_ml/common/seed.py`.

## Import Organization

**Order:**
1. Standard library imports first, for example `random` in `src/meshek_ml/common/seed.py` and `Path` in `src/meshek_ml/common/io.py`.
2. Third-party imports next, for example `numpy`, `pandas`, `gymnasium`, and `scipy`.
3. First-party `meshek_ml` imports last, for example in `src/meshek_ml/simulation/generator.py` and `src/meshek_ml/optimization/env.py`.

**Path Style:**
- Use absolute first-party imports from `meshek_ml`, not package-relative imports, across the codebase. Examples include `from meshek_ml.simulation.demand import generate_demand` in `src/meshek_ml/simulation/generator.py` and `from meshek_ml.optimization.rewards import CostParams, compute_reward` in `src/meshek_ml/optimization/env.py`.

## Module Organization

- Package boundaries are domain-oriented under `src/meshek_ml/`: `common`, `simulation`, `forecasting`, `optimization`, `federated`, and `demo`.
- Most modules are narrow and function-centric. A typical package splits schemas, helper math, and orchestration into separate files, as seen in `src/meshek_ml/simulation/schemas.py`, `src/meshek_ml/simulation/demand.py`, and `src/meshek_ml/simulation/generator.py`.
- `__init__.py` files are present but not used as heavy barrel files. Import directly from implementation modules rather than relying on package re-exports.
- Scripts in `scripts/` are thin entry points with a `main()` function and `if __name__ == "__main__":` guard, following `scripts/run_simulation.py`.

## Error-Handling Style

- Most computation modules do not wrap library exceptions. Functions rely on direct failure from pandas, NumPy, SciPy, or Gym APIs rather than custom exception hierarchies.
- Optional dependency handling uses narrow import guards. `src/meshek_ml/common/seed.py` catches `ImportError` around `torch` setup so the base package still works without the optimization extra.
- Placeholder modules signal incomplete work explicitly with `NotImplementedError`, for example `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/federated/client.py`, and `src/meshek_ml/federated/server.py`.
- Script-level placeholders prefer printing a status message instead of throwing, as in `scripts/run_forecast.py`, `scripts/run_optimization.py`, and `scripts/run_federated.py`.

## Repeated Implementation Patterns

- Favor pure functions that accept typed inputs and return DataFrames, ndarrays, tuples, or dictionaries without side effects, as in `src/meshek_ml/forecasting/evaluation.py`, `src/meshek_ml/federated/partitioning.py`, and `src/meshek_ml/optimization/newsvendor.py`.
- Copy input DataFrames before adding columns. `src/meshek_ml/forecasting/features.py` consistently starts transformations with `df = df.copy()` to avoid mutating caller state.
- Return defensive copies from partitioning helpers. `src/meshek_ml/federated/partitioning.py` uses `.copy()` on grouped or sliced frames before returning them.
- Use deterministic defaults around randomness. Many public APIs expose `seed: int = 42` or accept `np.random.Generator | None`, as seen in `src/meshek_ml/simulation/generator.py`, `src/meshek_ml/simulation/merchants.py`, `src/meshek_ml/simulation/demand.py`, and `src/meshek_ml/simulation/spoilage.py`.
- Domain constants live near the orchestrator that consumes them, for example `DEFAULT_PRODUCTS` in `src/meshek_ml/simulation/generator.py` and `ARCHETYPE_SPECS` in `src/meshek_ml/simulation/merchants.py`.
- Dataclass fields that hold mutable defaults use `field(default_factory=...)`, as in `src/meshek_ml/common/config.py`, `src/meshek_ml/simulation/schemas.py`, and `src/meshek_ml/simulation/spoilage.py`.
- The repository prefers small public APIs over inheritance-heavy designs. The main class-based exceptions are stateful domain objects such as `FIFOInventory` in `src/meshek_ml/simulation/spoilage.py` and `PerishableInventoryEnv` in `src/meshek_ml/optimization/env.py`.

## Planning Guidance

- Place new shared types, config objects, and IO helpers under `src/meshek_ml/common/` when they are reused across more than one domain package.
- Add new domain logic as a focused module under its package instead of growing orchestration files such as `src/meshek_ml/simulation/generator.py`.
- Keep optional integrations import-safe for base installs by following the local-import pattern already used in `src/meshek_ml/common/seed.py` and `src/meshek_ml/simulation/merchants.py`.
- When adding incomplete scaffolding, prefer explicit `NotImplementedError` in library code and a minimal explanatory `main()` in scripts so planning and testing can distinguish placeholders from production behavior.

---

*Convention analysis: 2026-03-24*
