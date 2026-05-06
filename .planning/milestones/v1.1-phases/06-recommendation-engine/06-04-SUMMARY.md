---
phase: 06-recommendation-engine
plan: 04
subsystem: recommendation
tags: [engine, facade, lifespan, fastapi, integration, three-tier]
requires: [phase-06-01, phase-06-02, phase-06-03]
provides:
  - meshek_ml.recommendation.engine:RecommendationEngine
  - meshek_ml.service.lifespan:build_lifespan
  - meshek_ml.service.lifespan:DEFAULT_MODEL_PATH
affects: [src/meshek_ml/recommendation/__init__.py, src/meshek_ml/service/__init__.py, tests/]
tech_stack:
  added: []
  patterns: [facade, asynccontextmanager, app-state-injection, fail-fast-startup]
key_files:
  created:
    - src/meshek_ml/recommendation/engine.py
    - src/meshek_ml/service/lifespan.py
    - tests/recommendation/test_engine.py
    - tests/recommendation/test_engine_integration.py
    - tests/service/__init__.py
    - tests/service/conftest.py
    - tests/service/test_lifespan.py
  modified:
    - src/meshek_ml/recommendation/__init__.py
    - src/meshek_ml/service/__init__.py
decisions: [D-01, D-10, D-11, D-12]
requirements: [REC-01, REC-02, REC-03, REC-04, INFRA-01]
metrics:
  duration: ~10m
  tasks: 2
  tests_added: 15
  tests_total_green: 120
  completed: 2026-04-14
---

# Phase 6 Plan 04: Wave 4 RecommendationEngine + FastAPI Lifespan Summary

Final Phase 6 wave. Wires the three tier functions behind a
`RecommendationEngine` façade and ships the `build_lifespan` FastAPI
factory that Phase 8 will import unchanged. Proven end-to-end with a
TestClient-driven lifespan test plus a three-tier engine integration
test that covers all five ROADMAP success criteria in one run.

## What Shipped

- **`meshek_ml.recommendation.engine.RecommendationEngine`** (NEW)
  - Stateless façade with `TIER_3_MIN_DAYS = 14` (D-01).
  - `recommend(merchant_id)` opens the merchant store via an injected
    `store_factory`, reads sales, then routes by
    `sales["date"].nunique()`. Branches on `.empty` FIRST (Pitfall 4)
    so zero-row DataFrames never raise before `nunique` is called.
  - Thresholds: `0 -> tier_1`, `1..13 -> tier_2`, `>=14 -> tier_3`.
  - Raises `RuntimeError` if Tier 3 is selected with no injected model —
    a clear signal that the lifespan hook did not run.
  - Re-exported from `meshek_ml.recommendation.__init__`.

- **`meshek_ml.service.lifespan.build_lifespan`** (NEW, INFRA-01)
  - Factory returns an `@asynccontextmanager` bound to a specific
    resolved path. Resolution order: explicit arg → `MESHEK_MODEL_PATH`
    env → `DEFAULT_MODEL_PATH` (`models/lightgbm_v1.bundle`).
  - Fail-fast: raises `RuntimeError("Model file not found ...")` at
    enter if the resolved path does not exist (T-6-12).
  - Loads the bundle via `load_model_bundle` (which enforces the
    `MESHEK_MODELS_DIR` traversal guard from Plan 03) and populates
    `app.state.ml` with an `AppState` instance — never a module-level
    global (Pitfall 3, T-6-14).
  - Clears `app.state.ml = None` on shutdown in a `try/finally`.
  - Re-exported from `meshek_ml.service.__init__` alongside `AppState`.

## Tests

- `tests/recommendation/test_engine.py` (8 tests)
  - Tier 1 routing at 0 days, Tier 2 at 1 and 13 days, Tier 3 at 14 and
    30 days, confidence bounds per tier, unknown merchant raises
    `UnknownMerchantError`, REC-04 response contract (non-null
    `reasoning_tier` and `confidence_score`).
- `tests/recommendation/test_engine_integration.py` (1 test)
  - `test_three_tiers_single_run`: one engine instance, three target
    merchants (0, 7, 30 days) plus two 14-day filler merchants so the
    Tier 2 pooled prior has inputs. Asserts the tier progression is
    `["category_default", "pooled_prior", "ml_forecast"]` and that
    every response carries the REC-04 fields. Covers ROADMAP success 1-5.
- `tests/service/test_lifespan.py` (6 tests, all `@pytest.mark.integration`)
  - Loads on startup (AppState populated with model, residual_std,
    non-empty feature_cols, correct model_path).
  - Missing file raises `RuntimeError("Model file not found ...")`.
  - Env var fallback (`MESHEK_MODEL_PATH`).
  - `_resolve_model_path(None)` returns `DEFAULT_MODEL_PATH` when no env.
  - **Loader called exactly once across 5 GET requests** (INFRA-01) via
    a monkeypatched counting wrapper around `load_model_bundle`.
  - Teardown clears `app.state.ml` to None.
- `tests/service/conftest.py` — session-scoped `model_bundle_path`
  fixture trains a real LightGBM bundle via `train_and_save` on
  `run_simulation(n_merchants=3, 2024-01-01 .. 2024-03-31, seed=42)`,
  pins `MESHEK_MODELS_DIR` for the session so the traversal guard
  accepts the tmp path, and restores any prior env value on teardown.

## Verification

```
$ .venv/bin/python -m pytest tests/recommendation/test_engine.py tests/recommendation/test_engine_integration.py -q --no-cov
9 passed in 1.90s

$ .venv/bin/python -m pytest tests/service/test_lifespan.py -q --no-cov
6 passed in 2.76s

$ .venv/bin/python -m pytest tests/recommendation tests/service tests/storage -q --no-cov
86 passed in 6.49s

$ .venv/bin/python -m pytest -q --no-cov
120 passed, 3 warnings in 15.28s
```

Full repo suite green (120 tests). Phase 5 storage, Phase 4
optimization, forecasting, and simulation suites all untouched.

## Decisions Applied

- **D-01** locked: tier threshold 14 distinct sale days for Tier 3.
- **D-10 / D-11 / D-12** realised: FastAPI lifespan factory, model
  loaded once at startup, state attached to `app.state` (never a
  module-level global).

Implementation-level choices:

- **`_resolve_model_path` is called at factory time, not at enter.**
  The env var is read once when `build_lifespan()` is invoked so the
  resolved path is fixed for the life of the factory. This matches the
  "read deploy config once" pattern in 06-RESEARCH §Pattern 1.
- **Engine `store_factory` is a callable, not a class reference.**
  Lets tests inject `lambda mid: MerchantStore(mid, must_exist=True)`
  and Phase 8 inject anything else (e.g., a caching wrapper) without
  touching the engine.

## Deviations from Plan

None of functional substance. Two minor process notes:

- **[Rule 3 — Blocking] `uv run pytest` fails on this machine.** Running
  `uv run pytest` triggers a full re-resolve which tries to build
  `pyarrow` from source (cmake missing). All prior Phase 6 plans used
  `.venv/bin/python -m pytest` directly and that works. I used the same
  invocation for this plan. Not a code change — just an execution-env
  workaround documented here so the next executor does not chase it.
- **`test_default_path_when_no_env` checks `_resolve_model_path`
  directly** rather than starting a TestClient (the default path
  `models/lightgbm_v1.bundle` does not exist in the test env, so
  asserting "startup resolves to the default" is equivalent to
  asserting the resolver returns the default — which is what we
  actually care about). Acceptance criterion ("resolved path ==
  DEFAULT_MODEL_PATH") is met exactly.

## Threat Model Follow-Up

- **T-6-12 (path traversal via `MESHEK_MODEL_PATH`): mitigated.** The
  env var is read once at factory time, never from a request. The
  underlying `load_model_bundle` additionally enforces
  `relative_to(MESHEK_MODELS_DIR)`. Covered transitively by Plan 03's
  `test_rejects_path_outside_models_dir` plus `test_missing_model_file`
  here.
- **T-6-13 (untrusted deserialization): mitigated at contract level.**
  Lifespan only loads the deploy-controlled path; documented in module
  docstring. Bundle validation (required keys present) inherited from
  Plan 03's `load_model_bundle`.
- **T-6-14 (cross-test / cross-request state leakage): mitigated.**
  State attaches to `app.state.ml`, never a module global. Every test
  constructs a fresh `FastAPI` instance. `test_teardown_clears_state`
  asserts cleanup.
- **T-6-15 (DoS via very large bundle): accepted.** v1.1 LightGBM
  bundles are <10MB.

No new threat surface introduced — no new network endpoints, no new
file access patterns beyond the already-modelled model bundle root.

## Phase 6 Complete

This plan is the last in Phase 6. All five ROADMAP must-haves are now
green:

1. Tier 1 returns category defaults for a 0-day merchant ✓
2. Tier 2 blends own and pooled means at 1..13 days ✓
3. Tier 3 ML-forecasts orders at ≥14 days ✓
4. Every response carries `reasoning_tier` and `confidence_score` ✓
5. Model bundle loaded once at FastAPI startup ✓ (loader counter == 1)

Phase 8 can now import `RecommendationEngine` and `build_lifespan`
unchanged.

## Self-Check: PASSED

Files verified present:
- FOUND: src/meshek_ml/recommendation/engine.py
- FOUND: src/meshek_ml/service/lifespan.py
- FOUND: tests/recommendation/test_engine.py
- FOUND: tests/recommendation/test_engine_integration.py
- FOUND: tests/service/__init__.py
- FOUND: tests/service/conftest.py
- FOUND: tests/service/test_lifespan.py
- FOUND: src/meshek_ml/recommendation/__init__.py (RecommendationEngine export)
- FOUND: src/meshek_ml/service/__init__.py (build_lifespan export)

Commits verified in git log:
- FOUND: ac7adcb feat(06-04): add RecommendationEngine facade with three-tier router
- FOUND: 839eca1 feat(06-04): add build_lifespan FastAPI factory (INFRA-01)
