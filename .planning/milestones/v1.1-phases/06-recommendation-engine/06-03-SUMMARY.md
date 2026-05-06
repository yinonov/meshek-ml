---
phase: 06-recommendation-engine
plan: 03
subsystem: recommendation
tags: [tier-3, lightgbm, model-io, newsvendor, traversal-guard]
requires: [phase-06-01, phase-06-02]
provides:
  - meshek_ml.recommendation.training:train_and_save
  - meshek_ml.recommendation.model_io:save_model_bundle
  - meshek_ml.recommendation.model_io:load_model_bundle
  - meshek_ml.recommendation.model_io:ModelBundle
  - meshek_ml.recommendation.tiers:tier_3_ml_forecast
affects: [tests/recommendation/]
tech_stack:
  added: []
  patterns: [joblib-persistence, path-traversal-guard, stateless-inference, newsvendor-normal]
key_files:
  created:
    - src/meshek_ml/recommendation/training.py
    - src/meshek_ml/recommendation/model_io.py
    - tests/recommendation/test_training.py
    - tests/recommendation/test_model_io.py
    - tests/recommendation/test_tier_3.py
  modified:
    - src/meshek_ml/recommendation/tiers.py
    - tests/recommendation/conftest.py
decisions: []
requirements: [REC-03, INFRA-01]
metrics:
  duration: ~8m
  tasks: 2
  tests_added: 15
  tests_total_green: 36
  completed: 2026-04-14
---

# Phase 6 Plan 03: Wave 3 LightGBM Training + Tier 3 Inference Summary

Wave 3 delivers REC-03 (Tier 3 ML-forecasted recommendations) without
touching the `forecasting.pipeline` public API. Training is a new
`recommendation.training.train_and_save` entry point that reuses the
low-level `forecasting.features.*` helpers so the training-time feature
set is bit-for-bit identical to the inference-time feature set (no
train/serve skew). Persistence goes through a guarded `model_io` module
that enforces a `MESHEK_MODELS_DIR` path-traversal boundary. Inference
(`tier_3_ml_forecast`) is stateless and consumes an already-loaded
bundle — the Plan 04 lifespan hook will own the single load at startup.

## What Shipped

- **`meshek_ml.recommendation.model_io`** (NEW)
  - `ModelBundle` TypedDict (`model`, `residual_std`, `feature_cols`).
  - `DEFAULT_MODELS_DIR = Path("models").resolve()` with
    `MESHEK_MODELS_DIR` env override re-read per call (so tests can
    `monkeypatch.setenv`).
  - `_assert_within_root(path)` uses `Path.resolve()` +
    `relative_to(root)` to reject any path outside the allowed root —
    T-6-08 mitigation. Both `save_model_bundle` and `load_model_bundle`
    run this guard before touching disk.
  - `load_model_bundle` additionally validates that all required keys
    are present (T-6-09) and raises `FileNotFoundError` if the file is
    absent.

- **`meshek_ml.recommendation.training`** (NEW)
  - `train_and_save(output_path, data)` is the sole offline training
    entry point for Tier 3. It deliberately does NOT import or call
    `run_forecast_pipeline` (that function is a train+evaluate harness
    with its own validation split). Acceptance criterion
    `! grep 'run_forecast_pipeline'` enforces this.
  - Mirrors the feature-engineering sequence from the pipeline:
    `normalize_simulation_data` -> `validate_demand_schema` -> sort ->
    `add_lag_features` -> `add_rolling_features` ->
    `add_calendar_features` -> `dropna`.
  - Trains via `forecasting.tree_models.train_lightgbm`, computes
    `residual_std = std(y_train - model.predict(x_train))`, and
    persists the bundle via `save_model_bundle` (same traversal
    guard). `FEATURE_COLS_TO_DROP` and `TARGET_COL` are mirrored as
    module constants rather than imported from `pipeline.py` to keep
    this module decoupled from the train+eval harness.

- **`meshek_ml.recommendation.tiers.tier_3_ml_forecast`** (APPENDED)
  - Feature engineering reuses the exact same `add_lag_features`,
    `add_rolling_features`, `add_calendar_features` calls as training.
  - Takes the latest date per product as the single inference row,
    imputes lag/rolling warmup NaNs with per-column means (Pitfall 1),
    predicts mu, and converts to an order quantity via
    `optimization.newsvendor.optimal_order_normal` with
    `residual_std` as sigma. Default costs `Cu=2.0, Co=1.0` (REC-07 deferred).
  - Confidence is a placeholder per Pitfall 2:
    `raw = 1 - residual_std / y_mean`, then `max(0.6, min(0.95, raw))`.
    The acceptance grep enforces the clip expression literally.
  - Inference is stateless — `tiers.py` imports neither `joblib` nor
    the bundle loader from `model_io` (acceptance greps). The
    monkeypatch test `test_inference_never_reads_disk` reinforces
    INFRA-01 by replacing `model_io.load_model_bundle` with a bomb
    and calling the inference function five times — it must never
    trigger.

- **`tests/recommendation/conftest.py`** (extended)
  - New session-scoped `trained_model_bundle` fixture uses
    `tmp_path_factory.mktemp("models-session")`, sets `MESHEK_MODELS_DIR`
    manually (session scope forbids the function-scoped `monkeypatch`
    fixture), trains on `run_simulation(n_merchants=3, 2024-01-01 ..
    2024-03-31, seed=42)`, and restores the previous env var on teardown.

## Tests

- `tests/recommendation/test_model_io.py` (5): save/load roundtrip,
  load-outside-root reject, save-outside-root reject,
  missing-keys reject, nonexistent-file reject. All sandboxed under
  `monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))`.
- `tests/recommendation/test_training.py` (5): bundle-keys present,
  loaded model predicts finite on zero-filled sample, residual_std > 0,
  feature_cols excludes `{date, merchant_id, product, quantity}`, and
  `test_pipeline_public_api_untouched` pins the
  `run_forecast_pipeline` parameter list via `inspect.signature`.
- `tests/recommendation/test_tier_3.py` (5): `reasoning_tier ==
  "ml_forecast"`, confidence in [0.6, 0.95], non-negative quantities,
  one rec per distinct product, inference-never-reads-disk (INFRA-01
  monkeypatch).

Full recommendation suite: **36 passed**. Phase 5 storage regression:
**35 passed**. `git diff HEAD~2 -- src/meshek_ml/forecasting/pipeline.py`
shows **0 lines** — pipeline public API is untouched.

```
$ .venv/bin/python -m pytest tests/recommendation -q --no-cov
36 passed in 4.65s

$ .venv/bin/python -m pytest tests/storage -q --no-cov
35 passed in 0.45s
```

## Decisions Made

No new context-level decisions. Implementation-level choices:

- **Constants mirrored, not imported.** `training.py` defines its own
  `TARGET_COL` and `FEATURE_COLS_TO_DROP` rather than importing from
  `forecasting.pipeline`. This keeps the new module structurally
  independent of the train+eval harness so future pipeline refactors
  cannot silently change training behaviour.
- **`MESHEK_MODELS_DIR` re-read per call.** Same pattern as
  `storage.merchant_store._data_root` — allows tests to override via
  `monkeypatch.setenv` and deployments to point at a persistent volume.
- **Default newsvendor costs (`Cu=2.0, Co=1.0`).** REC-07 (per-merchant
  cost parameters) is deferred; tier_3 hardcodes sensible defaults.

## Deviations from Plan

**[Rule 3 — Blocking] Test stub must be module-level.** The plan's
`test_save_load_roundtrip` template used a locally-defined `_Stub`
class inside `_fake_bundle()`. joblib cannot serialise function-local
classes by qualified name. Fix: promoted the stub to a module-level
`_StubModel` class. Functionally identical; unblocks the roundtrip
test. Committed in Task 1.

**[Rule 3 — Blocking] Tier 3 docstring phrasing vs. acceptance grep.**
The initial docstring mentioned the bundle loader by name, which
caused the `! grep -q 'load_model_bundle'` acceptance check to fail
on a prose reference. Rephrased to "never re-loads the bundle from
the filesystem" — semantic intent preserved, literal grep now passes.
Committed in Task 2.

Everything else executed exactly as written in the plan.

## Threat Model Follow-Up

- **T-6-08 (Tampering — path traversal): mitigated.** Both
  `save_model_bundle` and `load_model_bundle` call `_assert_within_root`
  which resolves the path and calls `relative_to(root)`, raising
  `ValueError` on escape. The allowed root comes from
  `MESHEK_MODELS_DIR` (defaults to `./models`), re-read per call.
  Enforced by `test_rejects_path_outside_models_dir` and
  `test_save_rejects_path_outside_models_dir` plus acceptance greps on
  `relative_to(root)` and `MESHEK_MODELS_DIR`.
- **T-6-09 (Tampering — untrusted load): mitigated at the contract
  level.** The module docstring documents that bundles are only loaded
  from files the service itself wrote to a deploy-controlled root. The
  loader rejects non-dict objects and any dict missing the required
  `ModelBundle` keys. REC-05 (retrain endpoint) will revisit hardening
  — deferred to v1.2.
- **T-6-10 (residual_std information disclosure): accepted.** Scalar
  aggregate, not PII.
- **T-6-11 (DoS via adversarial sales DataFrame): accepted.** Phase 5
  MerchantStore schema-validates writes; Tier 3 only reads from a
  validated store.

No new threat surface introduced — no new network endpoints, no new
file access patterns beyond the already-modelled models root.

## Self-Check: PASSED

Files verified present:
- FOUND: src/meshek_ml/recommendation/training.py
- FOUND: src/meshek_ml/recommendation/model_io.py
- FOUND: tests/recommendation/test_training.py
- FOUND: tests/recommendation/test_model_io.py
- FOUND: tests/recommendation/test_tier_3.py
- FOUND: src/meshek_ml/recommendation/tiers.py (tier_3_ml_forecast appended)
- FOUND: tests/recommendation/conftest.py (trained_model_bundle fixture)

Commits verified in git log:
- FOUND: cab3962 feat(06-03): add train_and_save entry point and safe model_io
- FOUND: bc5b3a8 feat(06-03): add tier_3_ml_forecast stateless inference
