---
phase: 09-model-bundle-pipeline
plan: "01"
subsystem: recommendation
tags: [lightgbm, training, cli, determinism, model-bundle]
dependency_graph:
  requires:
    - "06-03: train_and_save() and save/load_model_bundle()"
    - "07: run_simulation() in simulation.generator"
  provides:
    - "cli_train.py: deterministic offline training CLI"
    - "test_model_bundle.py: regression test suite for MODEL-02"
  affects:
    - "09-02: train-and-publish-model.sh consumes cli_train via python -m"
tech_stack:
  added: []
  patterns:
    - "argparse with env-var defaults (MESHEK_TRAIN_* prefix)"
    - "late imports inside main() for clean import-error traces"
    - "lightgbm.LGBMRegressor patched at lightgbm module level (not tree_models.lgb which is a local import)"
    - "in-process main() invocation via sys.argv monkeypatch (no subprocess)"
key_files:
  created:
    - src/meshek_ml/recommendation/cli_train.py
    - tests/recommendation/test_model_bundle.py
  modified: []
decisions:
  - "Patch lightgbm.LGBMRegressor directly (not meshek_ml.forecasting.tree_models.lgb.LGBMRegressor) because lgb is a local import inside train_lightgbm(), not a module attribute."
  - "MESHEK_TRAIN_N_MERCHANTS used as env var name (per user prompt) rather than MESHEK_TRAIN_MERCHANTS from research Pattern 5."
  - "Both tasks 9-01-01 and 9-01-02 committed in a single commit because test_deterministic_rerun was written as part of the same test file in the TDD flow."
metrics:
  duration: "~8 minutes"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 9 Plan 01: CLI Train + Regression Tests Summary

**One-liner:** Deterministic LightGBM training CLI (`cli_train.py`) wrapping `run_simulation` + `train_and_save` with env-var defaults and a 6-test regression suite proving bundle loadability and sub-1e-6 reproducibility.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 9-01-01 | Create cli_train.py + test_cli_produces_loadable_bundle | 26ad8e6 | src/meshek_ml/recommendation/cli_train.py, tests/recommendation/test_model_bundle.py |
| 9-01-02 | Add test_deterministic_rerun | 26ad8e6 (same commit) | tests/recommendation/test_model_bundle.py |

## What Was Built

### `src/meshek_ml/recommendation/cli_train.py`

Thin CLI wrapper (71 lines) that:
- Accepts `--seed`, `--n-merchants`, `--days`, `--output`, `--start-date` via argparse
- Env var defaults: `MESHEK_TRAIN_SEED=42`, `MESHEK_TRAIN_N_MERCHANTS=20`, `MESHEK_TRAIN_DAYS=180`, `MESHEK_TRAIN_OUTPUT=models/lightgbm_v1.bundle`
- Converts `--days` to `end_date = start + timedelta(days - 1)` (D-10 correction from research)
- Calls `run_simulation(n_merchants, start_date, end_date, seed)` — NOT the non-existent `generate_dataset()`
- Calls `train_and_save(output, data)` and emits a single JSON line: `{bundle_path, residual_std, feature_count, row_count, seed, n_merchants, days}`
- Does NOT set `MESHEK_MODELS_DIR` — caller owns the root (T-9-01-01, D-16)

### `tests/recommendation/test_model_bundle.py`

6 tests (89 lines):
- `test_bundle_round_trips` — `load_model_bundle` returns dict with keys `{model, residual_std, feature_cols}`
- `test_feature_cols_present` — 17 expected feature columns (lag + rolling + calendar)
- `test_residual_std_positive` — `residual_std > 0`
- `test_predict_shape` — `model.predict(zero_frame[:1])` returns finite `(1,)` array
- `test_cli_produces_loadable_bundle` — full in-process CLI invocation, JSON summary, load round-trip
- `test_deterministic_rerun` — two `train_and_save` calls on identical data, `abs(residual_std_diff) <= 1e-6`

All tests use `_patch_fast()` (n_estimators=20, num_leaves=7) via `lightgbm.LGBMRegressor` patch; full suite runs in 2.4s.

## Verification

```
.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q
# 6 passed in 2.41s

.venv/bin/python -m pytest tests -q --ignore=tests/deploy
# 217 passed, 1 skipped in 31.36s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Patch target corrected from tree_models.lgb to lightgbm.LGBMRegressor**
- **Found during:** Task 9-01-01 TDD RED phase
- **Issue:** Research §"Regression Test Shape" specified `patch("meshek_ml.forecasting.tree_models.lgb.LGBMRegressor", ...)` but `lgb` is a local import inside `train_lightgbm()` — it is not a module-level attribute. Running the patch raised `AttributeError: module 'meshek_ml.forecasting.tree_models' has no attribute 'lgb'`.
- **Fix:** Changed patch target to `"lightgbm.LGBMRegressor"`, which is the canonical object that the local `lgb.LGBMRegressor` reference resolves to. Behavior is identical.
- **Files modified:** tests/recommendation/test_model_bundle.py
- **Commit:** 26ad8e6

### Env Var Name

Research Pattern 5 used `MESHEK_TRAIN_MERCHANTS`; the user prompt's success criteria specified `MESHEK_TRAIN_N_MERCHANTS`. Used `MESHEK_TRAIN_N_MERCHANTS` throughout. Not a deviation from the plan spec — the plan action section explicitly calls out this choice.

## Known Stubs

None. All data is live (synthesised via `run_simulation`); no placeholder values flow to assertions.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes beyond those covered in the plan's threat model (T-9-01-01, T-9-01-02, T-9-01-03).

## Self-Check: PASSED

- `src/meshek_ml/recommendation/cli_train.py` — FOUND
- `tests/recommendation/test_model_bundle.py` — FOUND
- Commit 26ad8e6 — FOUND (`git log --oneline -1` confirms)
- All 6 `test_model_bundle.py` tests PASS (2.41s)
- Full suite 217 passed, 1 skipped, 0 failed
