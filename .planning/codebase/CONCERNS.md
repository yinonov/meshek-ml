# Codebase Concerns

**Analysis Date:** 2026-03-24

## Scope And Confidence

**Confirmed concerns:** Findings below are directly supported by checked-in code, config, scripts, or test behavior in `README.md`, `pyproject.toml`, `Makefile`, `src/meshek_ml/`, `tests/`, and `scripts/`.

**Hypotheses:** Items explicitly labeled as hypotheses are plausible planning risks inferred from current structure, but they are not proven runtime failures in this review.

## Tech Debt

**Federated learning surface is mostly placeholder code (confirmed):**
- Issue: The public federated entry points and strategy layer are declared but not implemented.
- Files: `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/strategies.py`, `src/meshek_ml/federated/federated_xgboost.py`, `src/meshek_ml/federated/personalization.py`, `scripts/run_federated.py`
- Impact: README and project structure advertise federated learning as a core pillar, but the runnable code path currently terminates in `NotImplementedError` or stub output.
- Fix approach: Implement one vertical slice first: partition data, define a concrete Flower client, define a server strategy, and wire `scripts/run_federated.py` through real config loading.

**Forecast orchestration is missing behind a completed-looking module layout (confirmed):**
- Issue: The forecasting package contains feature engineering, metrics, tree wrappers, Prophet wrapper, and Darts adapters, but `run_forecast_pipeline()` is unimplemented.
- Files: `src/meshek_ml/forecasting/pipeline.py`, `scripts/run_forecast.py`, `src/meshek_ml/forecasting/features.py`, `src/meshek_ml/forecasting/tree_models.py`, `src/meshek_ml/forecasting/prophet_model.py`, `src/meshek_ml/forecasting/darts_adapter.py`
- Impact: There is no canonical train/evaluate flow tying feature generation, split logic, model training, and metrics together, so downstream usage will fragment quickly.
- Fix approach: Build the pipeline around one supported model first, then add adapters behind a common evaluation contract.

**Demo layer is exposed but not actually implemented (confirmed):**
- Issue: The demo launch path exists, but the dashboard and scenarios modules are placeholders.
- Files: `scripts/run_demo.py`, `src/meshek_ml/demo/dashboard.py`, `src/meshek_ml/demo/scenarios.py`
- Impact: `make demo` and `scripts/run_demo.py` can launch Streamlit against a file with no functional app logic.
- Fix approach: Either remove the demo path from active workflow until implemented or ship a minimal working dashboard with one read-only scenario.

**CLI/config story is incomplete across non-simulation pillars (confirmed):**
- Issue: Multiple scripts promise Hydra-based execution but only print placeholder messages.
- Files: `scripts/run_forecast.py`, `scripts/run_optimization.py`, `scripts/run_federated.py`, `src/meshek_ml/common/config.py`, `configs/forecasting/prophet.yaml`, `configs/forecasting/lightgbm.yaml`, `configs/optimization/ppo.yaml`, `configs/federated/fedavg.yaml`, `configs/federated/fedprox.yaml`
- Impact: Config files and structured config classes exist, but there is no authoritative runtime path that consumes them outside simulation.
- Fix approach: Standardize script entrypoints on Hydra now, before pillar-specific command-line interfaces drift apart.

## Known Bugs And Integration Issues

**`prophet` is imported but not declared as a dependency (confirmed):**
- Symptoms: `create_prophet_forecast()` imports `from prophet import Prophet`, but `pyproject.toml` does not include `prophet` in base or optional dependencies.
- Files: `src/meshek_ml/forecasting/prophet_model.py`, `pyproject.toml`
- Trigger: Any forecasting path that exercises the Prophet wrapper in a clean environment.
- Workaround: Install `prophet` manually outside the declared extras.

**Advertised make targets route into placeholder implementations (confirmed):**
- Symptoms: `make forecast`, `make optimize`, and `make federate` resolve to scripts that only print not-implemented messages.
- Files: `Makefile`, `scripts/run_forecast.py`, `scripts/run_optimization.py`, `scripts/run_federated.py`
- Trigger: Following the project workflow implied by `README.md` and `Makefile`.
- Workaround: Use the lower-level implemented modules directly instead of the advertised commands.

**Holiday modeling uses acknowledged approximations that will drift from real dates (confirmed):**
- Symptoms: Israeli holidays are hard-coded to approximate Gregorian dates, and the docstring explicitly says a Hebrew calendar library is needed for production use.
- Files: `src/meshek_ml/simulation/calendar.py`
- Trigger: Simulating or forecasting across years where holiday timing materially affects demand.
- Workaround: Treat current holiday factors as synthetic scenario generation only, not production-grade calendar logic.

## Security Considerations

**No direct secret handling was detected in reviewed source paths (confirmed):**
- Risk: Low current exposure because the repository does not yet implement external service authentication in the reviewed code paths.
- Files: `pyproject.toml`, `src/meshek_ml/`, `scripts/`
- Current mitigation: External integrations are mostly not implemented yet.
- Recommendations: When federated networking or hosted demo features are added, introduce explicit secret loading boundaries and avoid embedding credentials in notebooks or configs.

**Runtime dependency execution from shell scripts will become a supply-chain boundary once integrations are added (hypothesis):**
- Risk: Current scripts execute imported third-party libraries directly with minimal runtime validation.
- Files: `scripts/run_demo.py`, `scripts/run_simulation.py`, `src/meshek_ml/forecasting/prophet_model.py`, `src/meshek_ml/forecasting/tree_models.py`, `src/meshek_ml/optimization/ppo_agent.py`
- Current mitigation: None beyond pinned minimum versions in `pyproject.toml`.
- Recommendations: Add environment validation and explicit dependency checks before long-running training or demo startup flows.

## Performance Bottlenecks

**Synthetic data generation builds the entire dataset in memory before concatenation (confirmed):**
- Problem: `run_simulation()` appends one DataFrame per merchant-product pair into `all_records` and performs a single `pd.concat()` at the end.
- Files: `src/meshek_ml/simulation/generator.py`
- Cause: The implementation favors simple batch assembly over streaming or chunked writes.
- Improvement path: Yield partitions incrementally or write per-merchant/product shards when scaling merchants, products, or date ranges.

**Forecast feature generation performs repeated grouped shifts and rolling transforms (confirmed):**
- Problem: `add_lag_features()` and `add_rolling_features()` perform one grouped transformation per lag/window.
- Files: `src/meshek_ml/forecasting/features.py`
- Cause: Straightforward pandas groupby logic is easy to read but scales poorly with large panel data.
- Improvement path: Benchmark larger synthetic datasets and consider vectorized or columnar backends before building end-to-end forecast training on top of it.

**Default boosting configurations are expensive and have no built-in early stopping or validation (confirmed):**
- Problem: Both LightGBM and XGBoost wrappers default to 500 estimators with no evaluation set or early stopping path.
- Files: `src/meshek_ml/forecasting/tree_models.py`
- Cause: Training wrappers only expose fit-once behavior.
- Improvement path: Add validation-aware training and surface early stopping parameters through the pipeline/config layer.

## Fragile Areas

**Optimization environment correctness is only shallowly tested and can silently drop from CI (confirmed):**
- Files: `src/meshek_ml/optimization/env.py`, `tests/optimization/test_env.py`
- Why fragile: The only environment test checks one reset/step path, and the whole file is skipped if `gymnasium` is unavailable.
- Safe modification: Change observation layout, reward mechanics, or episode rules only alongside stronger deterministic tests.
- Test coverage: No direct tests for invalid actions, reward edge cases, termination boundaries, or reproducibility.

**Reward shaping is central but untested (confirmed):**
- Files: `src/meshek_ml/optimization/rewards.py`
- Why fragile: Small coefficient changes can materially alter PPO behavior or business trade-offs, yet there is no direct test file for reward semantics.
- Safe modification: Lock a few canonical business scenarios in unit tests before tuning penalties.
- Test coverage: No direct coverage detected under `tests/optimization/`.

**The federated module boundary is unstable because only partitioning is implemented (confirmed):**
- Files: `src/meshek_ml/federated/partitioning.py`, `tests/federated/test_partitioning.py`, `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`
- Why fragile: One utility function is tested, but the rest of the subsystem is placeholders, so any new code will define the de facto architecture under time pressure.
- Safe modification: Decide the server-client-strategy interfaces before implementing multiple strategies in parallel.
- Test coverage: Only partitioning has tests.

## Scaling Limits

**Current optimization path is single-product while simulation is multi-product (confirmed):**
- Current capacity: `PerishableInventoryEnv` models a single-product inventory process, while simulation emits many merchants and products.
- Limit: There is no checked-in orchestration that closes the gap from multi-product demand tables to policy training or evaluation.
- Scaling path: Define a per-product policy abstraction first, then decide whether multi-SKU optimization is out of scope or requires a different environment.
- Files: `src/meshek_ml/optimization/env.py`, `src/meshek_ml/simulation/generator.py`

**Notebook-led exploration may become the only integration path if pipelines stay unimplemented (hypothesis):**
- Current capacity: There are notebooks for each pillar, but no comparable executable application flow for several of them.
- Limit: Reproducibility and automation degrade if the project relies on notebooks instead of scripts/pipelines.
- Scaling path: Promote one notebook workflow per pillar into tested Python entrypoints.
- Files: `notebooks/01_simulation_eda.ipynb`, `notebooks/02_demand_forecasting.ipynb`, `notebooks/03_inventory_optimization.ipynb`, `notebooks/04_federated_learning.ipynb`

## Missing Critical Features

**End-to-end forecasting execution is missing (confirmed):**
- Problem: The repository has model pieces but no train/split/evaluate pipeline.
- Blocks: Reproducible model comparison, CLI usage, and future federated forecasting integration.
- Files: `src/meshek_ml/forecasting/pipeline.py`, `scripts/run_forecast.py`

**End-to-end federated execution is missing (confirmed):**
- Problem: Client, server, strategy, XGBoost federation, and personalization are all placeholders.
- Blocks: The central product claim in `README.md`.
- Files: `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, `src/meshek_ml/federated/federated_xgboost.py`, `src/meshek_ml/federated/personalization.py`, `scripts/run_federated.py`

**Optimization training orchestration is missing (confirmed):**
- Problem: PPO helpers exist, but there is no real training/evaluation script or config-driven runner.
- Blocks: Repeatable experiments and benchmark comparison against the analytical newsvendor baseline.
- Files: `scripts/run_optimization.py`, `src/meshek_ml/optimization/ppo_agent.py`, `src/meshek_ml/optimization/evaluation.py`, `src/meshek_ml/optimization/newsvendor.py`

## Test Coverage Gaps

**Several source modules have no direct tests (confirmed):**
- What's not tested: `common/config`, `common/plotting`, `common/seed`, `forecasting/prophet_model`, `forecasting/tree_models`, `forecasting/darts_adapter`, `forecasting/pipeline`, `optimization/rewards`, `optimization/evaluation`, `optimization/ppo_agent`, `simulation/calendar`, `demo/dashboard`, `demo/scenarios`, `federated/client`, `federated/server`, `federated/strategies`, `federated/federated_xgboost`, `federated/personalization`.
- Files: `src/meshek_ml/common/config.py`, `src/meshek_ml/common/plotting.py`, `src/meshek_ml/common/seed.py`, `src/meshek_ml/forecasting/prophet_model.py`, `src/meshek_ml/forecasting/tree_models.py`, `src/meshek_ml/forecasting/darts_adapter.py`, `src/meshek_ml/forecasting/pipeline.py`, `src/meshek_ml/optimization/rewards.py`, `src/meshek_ml/optimization/evaluation.py`, `src/meshek_ml/optimization/ppo_agent.py`, `src/meshek_ml/simulation/calendar.py`, `src/meshek_ml/demo/dashboard.py`, `src/meshek_ml/demo/scenarios.py`, `src/meshek_ml/federated/client.py`, `src/meshek_ml/federated/server.py`, `src/meshek_ml/federated/strategies.py`, `src/meshek_ml/federated/federated_xgboost.py`, `src/meshek_ml/federated/personalization.py`
- Risk: Core claims can look implemented at the package level while remaining unverified at runtime.
- Priority: High

**Current test suite validates the stable core but not optional heavy-dependency paths (confirmed):**
- What's not tested: Prophet, Darts, LightGBM, XGBoost, PPO training, Streamlit launch path, and real Flower integration.
- Files: `pyproject.toml`, `tests/`, `src/meshek_ml/forecasting/prophet_model.py`, `src/meshek_ml/forecasting/darts_adapter.py`, `src/meshek_ml/forecasting/tree_models.py`, `src/meshek_ml/optimization/ppo_agent.py`, `src/meshek_ml/demo/dashboard.py`, `src/meshek_ml/federated/`
- Risk: `pytest` currently passes in the project venv (`20 passed, 1 skipped`), but that success mostly reflects the implemented lightweight core rather than the advertised full stack.
- Priority: High

---

*Concerns audit: 2026-03-24*
