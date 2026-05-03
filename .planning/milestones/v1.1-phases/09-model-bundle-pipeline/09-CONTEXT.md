# Phase 9: Model Bundle Pipeline - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning
**Mode:** Auto (autonomous workflow, --only 9)

<domain>
## Phase Boundary

Ship a reproducible pipeline that trains a LightGBM model bundle from
synthetic seed data, publishes it to a versioned GCS location, and wires
the live Cloud Run service to load it at startup so `/health` flips to
200 and Tier 3 ML-forecasted recommendations work end-to-end.

This phase delivers: the train-and-publish script, a second GCS bucket
for model artifacts, a second Cloud Run GCS FUSE mount for the model
directory, a Cloud Run revision that loads the model, a bundle
regression test, and operator documentation. It does NOT deliver
per-merchant retraining, an async `POST /retrain` endpoint, model
registry/experiment tracking, federated training, or automated model
promotion.

</domain>

<decisions>
## Implementation Decisions

### Model Source Strategy
- **D-01:** Use option #2 — **second GCS FUSE mount** at `/app/models`.
  The model bundle lives in `gs://meshek-prod-models/lightgbm_v1.bundle`
  and Cloud Run mounts that bucket at `/app/models` via a second
  `--add-volume ... type=cloud-storage` flag. No rebuild to ship a new
  model — uploading a new object and redeploying (or waiting for the
  next cold start) picks it up.
- **D-02:** NOT baked into the Docker image — option #1 rejected because
  every retrain would require a full image rebuild + deploy. Option #3
  (startup downloader) rejected because FUSE already gives us the same
  UX with less code.

### GCS Bucket
- **D-03:** New bucket `gs://meshek-prod-models`, region `me-west1`,
  uniform bucket-level access, versioning ON, 90-day non-current version
  retention (longer than the merchants bucket because model artifacts
  are more precious).
- **D-04:** Bucket creation is idempotent and handled by a new step in
  `scripts/bootstrap-cloudrun.sh` — rerun is safe.
- **D-05:** The Cloud Run service account
  `meshek-ml-run@meshek-prod.iam.gserviceaccount.com` gets
  `roles/storage.objectViewer` on this bucket (read-only — service never
  writes to the model bucket, training is offline).

### Cloud Run Wiring
- **D-06:** Extend `scripts/deploy-cloudrun.sh` to pass a SECOND volume
  pair in addition to the merchants mount:
    - `--add-volume name=models-vol,type=cloud-storage,bucket=meshek-prod-models,readonly=true`
    - `--add-volume-mount volume=models-vol,mount-path=/app/models`
  The existing `MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle` env
  var (Phase 8.1 D-23) then resolves through the FUSE mount. Zero code
  changes in `service/lifespan.py`.
- **D-07:** `readonly=true` on the models volume — the service cannot
  accidentally corrupt the model bundle. Training is a separate
  operator action.
- **D-08:** Keep `MESHEK_MODELS_DIR=/app/models` wired (already set in
  Phase 8.1 env vars) so the `relative_to()` traversal guard in
  `load_model_bundle` has the right root.

### Training Script
- **D-09:** New script `scripts/train-and-publish-model.sh` (bash
  entrypoint) that:
    1. Runs `python -m meshek_ml.recommendation.cli_train` (new small
       CLI wrapper, see D-10) with a deterministic seed
    2. Verifies the bundle loads cleanly via
       `meshek_ml.recommendation.model_io.load_model_bundle`
    3. Uploads to `gs://meshek-prod-models/lightgbm_v1.bundle` via
       `gcloud storage cp`
    4. Prints the GCS generation number so the operator can pin a
       specific version if needed
- **D-10:** New thin CLI module `src/meshek_ml/recommendation/cli_train.py`
  (or `__main__.py`) that wraps `train_and_save()`:
    - Generates a deterministic synthetic dataset via the existing
      `simulation.generator.generate_dataset(...)` with a fixed seed
      (`MESHEK_TRAIN_SEED=42`) and configurable merchant count /
      history length (defaults: `n_merchants=20`, `days=180`)
    - Writes the bundle to a configurable local path (default:
      `models/lightgbm_v1.bundle`)
    - Exits 0 on success with a JSON line summary: `{bundle_path,
      residual_std, feature_count, row_count}`
- **D-11:** Deterministic reproducibility check: running the script
  twice in a clean tree with the same seed MUST produce a bundle whose
  `feature_cols` and `residual_std` match to ≤1e-6. Tested in the
  regression test.
- **D-12:** Upload step uses `gcloud storage cp --cache-control=no-cache`
  so FUSE-mounted readers always see the latest generation on cold
  start. `gcloud` is the only dependency; no `google-cloud-storage`
  Python client added.
- **D-13:** Script is idempotent: `DRY_RUN=1` prints the gcloud cp
  command without uploading. `LOCAL_ONLY=1` trains and writes the
  bundle but skips the GCS upload (for local smoke tests).

### Regression Test
- **D-14:** New test `tests/recommendation/test_model_bundle.py`:
    - Fixture: generate a tiny synthetic dataset (5 merchants, 30 days)
      and run `train_and_save()` into a tmpdir
    - Assertions:
        - `load_model_bundle` round-trips the dict cleanly
        - `feature_cols` is non-empty and contains the lag/rolling
          columns we expect
        - `residual_std > 0`
        - `model.predict(X[:1])` returns a 1-element float array
        - A re-run with the same seed produces byte-identical
          `feature_cols` + `residual_std` (determinism check for D-11)
- **D-15:** Test runs in under 5 seconds — use tiny LightGBM params
  (`n_estimators=20`, `num_leaves=7`) if the default is slow.

### Service Integration (Zero Code Changes)
- **D-16:** `src/meshek_ml/service/lifespan.py` is NOT touched. The
  existing `build_lifespan()` already reads `MESHEK_MODEL_PATH` and
  `load_model_bundle` already enforces `MESHEK_MODELS_DIR` traversal.
  Phase 9 just ensures the FUSE mount populates those paths at
  runtime.
- **D-17:** `src/meshek_ml/service/app.py` `_build_engine_lifespan`
  degraded-start path continues to work unchanged — if the FUSE mount
  is missing for any reason (bucket empty, IAM misconfig), the service
  still boots in degraded mode rather than crashing.

### Deployment Flow
- **D-18:** Operator workflow after Phase 9:
    1. `./scripts/bootstrap-cloudrun.sh` — now also creates the models
       bucket + grants IAM (idempotent on rerun)
    2. `./scripts/train-and-publish-model.sh` — trains + uploads
    3. `./scripts/deploy-cloudrun.sh` — redeploys with the second
       volume pair
    4. Verify `/health` → 200 + `{model_loaded: true}`
    5. Verify `POST /recommend` for a merchant with ≥14 days of
       seeded sales returns `reasoning_tier: "ml_forecast"`
- **D-19:** No auto-reload: Cloud Run caches the FUSE mount per
  revision. To ship a new model, upload + redeploy (a no-op deploy
  with the same image tag is fine — `gcloud run services update`
  bumps the revision and refreshes FUSE).

### Observability
- **D-20:** `/health` response body gains no new fields — `model_loaded`
  is already there from Phase 8 D-10. No new routes or metrics.
- **D-21:** The Phase 8 JSON logger will log the model load success
  message at startup via the existing lifespan warning path; Cloud
  Logging picks it up automatically.

### Documentation
- **D-22:** Extend `docs/deploy-cloudrun.md` with a new section
  "Training and publishing a model bundle" covering the train script,
  reproducibility expectations, GCS generation pinning, how to roll
  back to a prior version (gcloud storage object restore), and how to
  force a no-op Cloud Run redeploy to pick up a new bundle.
- **D-23:** Document the read-only design decision and why the service
  account gets `objectViewer` not `objectUser` on the models bucket.

### Testing (local)
- **D-24:** All existing Phase 8 / 8.1 tests must continue to pass
  unchanged.
- **D-25:** The `test_model_bundle.py` regression test is the only new
  unit test. Run with `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q`.
- **D-26:** Docker smoke test unchanged — no image rebuild needed for
  Phase 9 since we're not changing the Dockerfile.

### Out of Scope (explicitly deferred)
- **D-27:** Per-merchant model retraining — REC-05 / v2
- **D-28:** `POST /retrain/{merchant_id}` async endpoint — REC-05 / v2
- **D-29:** Federated training across merchants — OPT-02 / v2
- **D-30:** Model registry / experiment tracking — Trackio is wired in
  the simulation repo but intentionally not gated into the service
  training path
- **D-31:** Automated model promotion / canary — operator manually
  redeploys for v1.1
- **D-32:** Training on real merchant data — Phase 9 uses synthetic
  data only. Real data pipeline belongs in a future "data ingestion"
  phase
- **D-33:** Model quality metrics / evaluation dashboard — the
  forecasting repo has this; the service doesn't need it for v1.1
- **D-34:** A/B testing two bundles — single-bundle-at-a-time for v1.1
- **D-35:** Pinning generation numbers in deploy flags — we trust
  `:latest` via the FUSE mount; SEED-001 can revisit if needed

### Claude's Discretion
- Exact LightGBM hyperparameters in the tiny test fixture
- Whether `cli_train.py` uses argparse or just env vars
- Whether the train script writes a sidecar metadata JSON
  (`lightgbm_v1.bundle.meta.json`) alongside the bundle with
  training timestamp and row count — nice-to-have, not required
- Exact log messages in the train script

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/ROADMAP.md` — Phase 9 goal + success criteria (7 of them)
- `.planning/REQUIREMENTS.md` §MODEL-01, MODEL-02

### Upstream Phase Context
- `.planning/phases/08-api-surface-deployment/08-CONTEXT.md` — Phase 8
  D-10 (`/health` degraded-start), D-19 (model bundle path), D-23
  (env var wiring)
- `.planning/phases/08.1-cloud-run-deployment/08.1-CONTEXT.md` —
  all D-06..D-23 — the Cloud Run deploy flags Phase 9 extends
- `.planning/phases/08.1-cloud-run-deployment/08.1-VERIFICATION.md`
  — live deploy evidence; Phase 9 redeploys on top of the same
  revision chain

### Related Seeds
- `.planning/seeds/SEED-001-gcp-native-storage-migration.md` — future
  Cloud SQL migration. Phase 9's model bucket is unaffected by that
  migration.

### Existing Code
- `src/meshek_ml/recommendation/training.py::train_and_save` — the
  entry point we wrap. Already takes `(output_path, data)` and
  enforces the `MESHEK_MODELS_DIR` traversal guard on write.
- `src/meshek_ml/recommendation/model_io.py::save_model_bundle` /
  `load_model_bundle` — joblib round-trip with path validation
- `src/meshek_ml/simulation/generator.py` — synthetic dataset
  generator (`generate_dataset(n_merchants, days, seed=...)`)
- `src/meshek_ml/forecasting/features.py` — lag/rolling/calendar
  feature engineering (train-inference parity guarantee)
- `src/meshek_ml/service/lifespan.py::build_lifespan` — reads
  `MESHEK_MODEL_PATH`, enforces traversal via `MESHEK_MODELS_DIR`
- `scripts/bootstrap-cloudrun.sh` — extend to create the models
  bucket
- `scripts/deploy-cloudrun.sh` — extend to pass the second volume
  pair

### External
- Cloud Run GCS FUSE volume mounts — multiple volumes are supported;
  cite: https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts
- Cloud Storage generation numbers — for version pinning docs:
  https://cloud.google.com/storage/docs/object-versioning
- `gcloud storage cp` reference —
  https://cloud.google.com/sdk/gcloud/reference/storage/cp

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `train_and_save()` already exists, validated, and path-guarded. Wrap
  it with a tiny CLI, nothing more.
- `simulation.generator.generate_dataset()` is seeded and deterministic —
  reuse it verbatim for training data.
- `load_model_bundle` in `model_io.py` already validates
  `relative_to(MESHEK_MODELS_DIR)` traversal — the FUSE mount at
  `/app/models` with `MESHEK_MODELS_DIR=/app/models` satisfies this
  out of the box.
- `scripts/bootstrap-cloudrun.sh` pattern (from Phase 8.1) for idempotent
  GCS resource creation — copy the bucket-create block and adjust.
- `scripts/deploy-cloudrun.sh` already passes one volume pair; adding
  a second is two additional `--add-volume` / `--add-volume-mount`
  flags. Trivial.

### Established Patterns
- `scripts/` hosts all bash entry points, `set -euo pipefail`,
  `DRY_RUN=1` flag support
- Tests under `tests/recommendation/` — existing module has tests for
  tiers and config
- Env vars with `MESHEK_` prefix, sensible defaults, documented in the
  Dockerfile and deploy script

### Integration Points
- FUSE mount at `/app/models` + `MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle`
  = zero code changes in the service layer
- `MESHEK_MODELS_DIR=/app/models` (Phase 8.1 D-23 already sets this)
  keeps the traversal guard happy
- Redeploy path is the existing `scripts/deploy-cloudrun.sh` with the
  extra volume pair baked in

</code_context>

<specifics>
## Specific Ideas

- Reproducibility is the load-bearing quality — two runs with the same
  seed must produce bundles with identical `feature_cols` and
  `residual_std` to ≤1e-6. This is what makes the v1.1 model pipeline
  auditable.
- Synthetic data is the right training source for v1.1 because there
  is no production merchant data yet (Phase 8.1 just went live — the
  only two merchants are from the smoke test).
- `readonly=true` on the models FUSE volume is defense-in-depth —
  even if the service had a bug, it physically cannot overwrite the
  model bundle in production.
- Operator UX goal: a new engineer can train + deploy a fresh model
  in under 5 minutes with three commands (bootstrap, train, deploy).
- Keep the train script bash-with-python-inside, not Python all the
  way down. Matches Phase 8.1's deploy script style and keeps the
  gcloud invocation visible.

</specifics>

<deferred>
## Deferred Ideas

- REC-05 async retrain endpoint — v2
- Per-merchant model retraining — v2 (needs real data pipeline first)
- Federated training / OPT-02 — v2
- Model registry / Trackio integration — post-v1.1 observability phase
- Automated canary deploys of new model bundles — future
- Training on real merchant data — requires a data ingestion pipeline
  phase (out of scope for v1.1)
- Model quality dashboards / backtests inside the service — the
  `forecasting/` package already has these; they don't need to run
  on Cloud Run

</deferred>

---

*Phase: 09-model-bundle-pipeline*
*Context gathered: 2026-04-15 (auto mode — /gsd-autonomous --only 9)*
