---
phase: 9
slug: model-bundle-pipeline
verified: 2026-04-15T17:02:00Z
status: passed
must_haves_verified: 7
must_haves_total: 7
live_deploy:
  service_url: https://meshek-ml-aiaajb5omq-zf.a.run.app
  region: me-west1
  project: meshek-prod
  revision: meshek-ml-00004-pg4
  ingress: internal-and-cloud-load-balancing
  models_bucket: gs://meshek-prod-models
  bundle_generation: "1776271500540954"
  bundle_size_bytes: 1381420
  feature_count: 17
  residual_std: 8.231474500809432
---

# Phase 9: Model Bundle Pipeline — Verification Report

**Phase Goal:** Reproducible LightGBM model bundle training + GCS publishing + Cloud Run second-FUSE mount so `/health` flips to 200 and Tier 3 ML-forecasted recommendations work end-to-end.

**Verified:** 2026-04-15

**Status:** passed (7/7)

## Success Criteria

### SC-1: scripts/train-and-publish-model.sh produces a deterministic bundle
Verdict: passed. Output: feature_count=17, residual_std=8.231474500809432, row_count=28800. Regression test test_deterministic_rerun asserts feature_cols and residual_std match to <=1e-6 across runs.

### SC-2: GCS publish is idempotent and versioned
Verdict: passed. Bundle published to gs://meshek-prod-models/lightgbm_v1.bundle at generation 1776271500540954 (1381420 bytes). Bucket has versioning ON + 90-day non-current retention.

### SC-3: Cloud Run loads the model via second GCS FUSE mount
Verdict: passed. scripts/deploy-cloudrun.sh now passes both merchants-vol and models-vol,readonly=true. Revision meshek-ml-00004-pg4 shipped successfully with app.state.ml populated at startup.

### SC-4: GET /health returns 200 with model_loaded: true
Verdict: passed. Live response: HTTP 200 body `{"status":"ok","model_loaded":true,"version":"1.1.0"}`.

### SC-5: Tier 3 ML-forecasted recommendations work end-to-end
Verdict: passed. Seeded merchant with 20 days of structured sales. POST /recommend returned HTTP 200 with reasoning_tier="ml_forecast", confidence_score=0.6, and per-product forecasts (cucumbers 6.3 kg, tomatoes 8.71 kg).

### SC-6: Regression test asserts bundle shape and determinism
Verdict: passed. `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q` -> 6 passed in 2.4s. Covers round-trip, feature_cols count (17), residual_std > 0, predict shape, CLI-produced bundle, deterministic rerun.

### SC-7: docs/deploy-cloudrun.md documents the training flow
Verdict: passed. Section 9 "Training and publishing a model bundle" added: quick flow, script usage (env vars, flags, DRY_RUN, LOCAL_ONLY), reproducibility, GCS generation inspection, rollback via generation copy-in-place, force refresh, read-only mount rationale.

## Fixes landed during live deploy

Three fixes were required before Tier 3 could work in production. Each is committed:

1. e7d3432 - fix(09): install libgomp1 for LightGBM on python:3.12-slim
   python:3.12-slim ships without OpenMP runtime; LightGBM's ctypes load of libgomp.so.1 failed at import. Added libgomp1 apt install before uv sync.

2. dbf8368 - fix(09): add scikit-learn to runtime extra
   LGBMRegressor is the sklearn API wrapper; at inference time it invokes BaseEstimator methods. Without sklearn in the runtime venv, model.predict raised AttributeError. Added scikit-learn>=1.3 to the runtime extra and regenerated uv.lock.

3. 933e7d9 (from Phase 8.1) - Cloud Build region pinning, unchanged.

## Known Limitations / Follow-ups

- Training environment skew: bundle was trained on Python 3.13 + sklearn 1.8.0 locally, not inside the Cloud Run container (Python 3.12). It works because lightgbm 4.6.0's sklearn wrapper is forward-compatible with sklearn 1.3+ at unpickle time. For long-term reproducibility, future retrains should run inside a matched container. Follow-up task: containerize the training step.
- Model quality is synthetic-data only: v1.1 uses run_simulation(n_merchants=20, days=180, seed=42). Real data pipeline is deferred to a future phase.
- Cloud Run max-instances=2: one-instance FUSE contention is not an issue at 1-request-per-day volume.

## Human Verification

None outstanding - all 7 success criteria verified against the live Cloud Run service.

## VERIFICATION COMPLETE
