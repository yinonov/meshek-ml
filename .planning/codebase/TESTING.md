# Testing Patterns

**Analysis Date:** 2026-03-24

## Test Framework

**Runner:**
- Pytest is the active test runner, configured in `pyproject.toml` under `[tool.pytest.ini_options]`.
- Test discovery is limited to `tests/`, and default options are `-v --tb=short`.

**Assertion Library:**
- The suite uses plain pytest assertions plus library-specific helpers such as `pd.testing.assert_frame_equal` in `tests/common/test_io.py`.

**Run Commands:**
```bash
pytest                          # Run all tests
pytest -m "not slow"            # Skip slow tests
pytest --cov=src/meshek_ml      # Coverage via pytest-cov extra
```

## Test File Organization

**Location:**
- Tests live in top-level package-mirrored directories under `tests/`: `tests/common/`, `tests/simulation/`, `tests/forecasting/`, `tests/optimization/`, and `tests/federated/`.
- There are no tests under `tests/demo/`, which matches the absence of demo coverage in the current suite.

**Naming:**
- Files use `test_<module>.py`, for example `tests/simulation/test_spoilage.py` and `tests/optimization/test_env.py`.
- Tests are plain functions named `test_<behavior>`; there are no `Test*` classes.

**Structure:**
```text
tests/
├── conftest.py
├── common/test_io.py
├── forecasting/test_evaluation.py
├── forecasting/test_features.py
├── optimization/test_env.py
├── optimization/test_newsvendor.py
├── simulation/test_demand.py
├── simulation/test_generator.py
├── simulation/test_merchants.py
├── simulation/test_spoilage.py
└── federated/test_partitioning.py
```

## Shared Fixtures And Data Setup

- Shared fixtures live in `tests/conftest.py`.
- `sample_dates()` provides a deterministic `pd.date_range` for January 2024.
- `sample_demand_df(sample_dates)` builds a minimal demand DataFrame using `np.random.default_rng(42)`, which sets the pattern for deterministic synthetic test data.
- Fixture scope is the default function scope; no session-wide or autouse fixtures are used.
- Temporary filesystem tests use pytest built-ins directly, as in `tmp_path` from `tests/common/test_io.py`.

## Current Coverage Focus Areas

**Common utilities:**
- `tests/common/test_io.py` covers parquet round-tripping for `src/meshek_ml/common/io.py`.

**Simulation:**
- `tests/simulation/test_demand.py` covers output shape, non-negative demand, and merchant scaling behavior for `src/meshek_ml/simulation/demand.py`.
- `tests/simulation/test_merchants.py` covers merchant count and unique IDs for `src/meshek_ml/simulation/merchants.py`.
- `tests/simulation/test_spoilage.py` covers quality decay, FIFO selling, expiration, and stockout handling for `src/meshek_ml/simulation/spoilage.py`.
- `tests/simulation/test_generator.py` acts as a slow orchestration check for `src/meshek_ml/simulation/generator.py` by validating expected row counts and key columns.

**Forecasting:**
- `tests/forecasting/test_features.py` verifies feature-column creation for `src/meshek_ml/forecasting/features.py`.
- `tests/forecasting/test_evaluation.py` checks exact or near-exact metric values for `src/meshek_ml/forecasting/evaluation.py`.

**Optimization:**
- `tests/optimization/test_newsvendor.py` validates closed-form behavior in `src/meshek_ml/optimization/newsvendor.py`.
- `tests/optimization/test_env.py` smoke-tests reset and one environment step for `src/meshek_ml/optimization/env.py`.

**Federated:**
- `tests/federated/test_partitioning.py` covers partition cardinality and conservation of rows for `src/meshek_ml/federated/partitioning.py`.

## Test Structure Patterns

- Import the concrete functions under test at module top level when the dependency is always available, as in `tests/forecasting/test_evaluation.py` and `tests/simulation/test_spoilage.py`.
- Use `pytest.importorskip()` inside a test module when the implementation depends on an optional extra, as in `tests/optimization/test_env.py` for `gymnasium`.
- Prefer simple invariant assertions over heavy fixture setup. Examples include column existence checks in `tests/forecasting/test_features.py` and inequality checks on means in `tests/simulation/test_demand.py`.
- For numerics, the suite currently uses direct comparisons with tolerances via `abs(... - expected) < 1e-6` rather than `pytest.approx`, as seen in `tests/forecasting/test_evaluation.py` and `tests/optimization/test_newsvendor.py`.
- Integration-style tests are marked explicitly with `@pytest.mark.slow`, currently used in `tests/simulation/test_generator.py`.

## Mocking And Optional Dependencies

**Framework:**
- No dedicated mocking framework usage is present. There is no observed use of `unittest.mock`, pytest monkeypatch, or external HTTP mocking tools.

**Patterns:**
- The suite currently avoids mocking and instead exercises small pure functions directly.
- Optional dependencies are handled by skipping tests when the extra is not installed, following `tests/optimization/test_env.py`.

**What To Mock:**
- If new tests reach script entry points in `scripts/` or future external-service code in `src/meshek_ml/federated/`, mock side effects at the boundary and preserve the current preference for real computation in core functions.

**What Not To Mock:**
- Do not mock NumPy, pandas, or deterministic helper functions in pure modules like `src/meshek_ml/forecasting/evaluation.py`, `src/meshek_ml/federated/partitioning.py`, and `src/meshek_ml/optimization/rewards.py`.

## How To Add Tests Consistently

- Put each new test module in the mirrored package directory under `tests/`, for example code added in `src/meshek_ml/common/config.py` should be tested in `tests/common/test_config.py`.
- Reuse `tests/conftest.py` for shared DataFrame fixtures instead of rebuilding the same setup in multiple files.
- Keep tests function-based unless a module genuinely needs expensive shared setup.
- Seed all stochastic behavior explicitly with `42` or pass a `np.random.default_rng(42)` so assertions remain stable across runs.
- For DataFrame-producing functions, assert both schema and behavioral invariants. Follow `tests/common/test_io.py` for exact frame equality and `tests/simulation/test_demand.py` for column and range checks.
- For optional extras such as Gym, Torch, Flower, Darts, Prophet, or Streamlit, gate tests with `pytest.importorskip()` in the same style as `tests/optimization/test_env.py`.
- Use the existing `slow` marker for full-pipeline or larger synthetic-data checks. The `integration` marker is defined in `pyproject.toml` but not used in the current suite; new cross-module flows can adopt it consistently.

## Likely Coverage Gaps

**Common package:**
- `src/meshek_ml/common/config.py`, `src/meshek_ml/common/seed.py`, and `src/meshek_ml/common/plotting.py` have no corresponding tests.

**Simulation package:**
- `src/meshek_ml/simulation/calendar.py` and `src/meshek_ml/simulation/schemas.py` are untested directly.

**Forecasting package:**
- `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/forecasting/tree_models.py`, `src/meshek_ml/forecasting/darts_adapter.py`, and `src/meshek_ml/forecasting/prophet_model.py` have no observed tests.

**Optimization package:**
- `src/meshek_ml/optimization/rewards.py`, `src/meshek_ml/optimization/evaluation.py`, and `src/meshek_ml/optimization/ppo_agent.py` are not covered.

**Federated package:**
- Only `src/meshek_ml/federated/partitioning.py` is tested. `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, `src/meshek_ml/federated/personalization.py`, and `src/meshek_ml/federated/federated_xgboost.py` have no observed coverage.

**Demo and scripts:**
- `src/meshek_ml/demo/dashboard.py`, `src/meshek_ml/demo/scenarios.py`, and all script entry points in `scripts/` are currently untested.

## Risk Notes For Future Planning

- The heaviest tested path is simulation; this is the most stable place to build from when adding integration tests.
- Placeholder modules that raise `NotImplementedError` should get tests that assert the current contract first, then be replaced with behavior tests once implemented. Relevant files are `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/federated/client.py`, and `src/meshek_ml/federated/server.py`.
- Because the suite has little mocking and no browser or API testing harness, new tests should continue prioritizing deterministic library-level checks unless the repository adopts a wider integration strategy.

---

*Testing analysis: 2026-03-24*
