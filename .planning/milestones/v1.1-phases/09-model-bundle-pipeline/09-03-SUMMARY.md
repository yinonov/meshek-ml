---
phase: 09-model-bundle-pipeline
plan: "03"
subsystem: infrastructure
tags: [gcs, cloud-run, fuse, bootstrap, deploy, iam]
dependency_graph:
  requires: ["09-02"]
  provides: ["gs://meshek-prod-models bucket provisioning", "Cloud Run second FUSE mount for /app/models"]
  affects: ["scripts/bootstrap-cloudrun.sh", "scripts/deploy-cloudrun.sh"]
tech_stack:
  added: []
  patterns:
    - "idempotent describe||create pattern for GCS buckets"
    - "multi-volume Cloud Run FUSE mounts via --add-volume pairs"
key_files:
  modified:
    - scripts/bootstrap-cloudrun.sh
    - scripts/deploy-cloudrun.sh
decisions:
  - "MESHEK_MODELS_DIR was missing from ENV_VARS in deploy-cloudrun.sh (D-08 claimed Phase 8.1 set it — it had not). Added in this plan."
  - "readonly=true lowercase exact string used per Pitfall 4 / official Cloud Run docs."
  - "objectViewer role used on models bucket (not objectUser) — service never writes bundles."
metrics:
  duration: "~5 minutes"
  completed: "2026-04-15"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
  commits: 2
---

# Phase 09 Plan 03: Bootstrap + Deploy Script Extensions for 2nd FUSE Mount Summary

**One-liner:** Idempotent `gs://meshek-prod-models` bucket provisioning (me-west1, versioning, 90-day lifecycle, objectViewer IAM) plus second Cloud Run FUSE volume pair (`models-vol → /app/models`) wired into both operator scripts.

## What Was Built

Extended the two existing operator scripts to wire the models GCS bucket and Cloud Run FUSE mount needed for MODEL-01 end-to-end:

- **`scripts/bootstrap-cloudrun.sh`** — new block that idempotently creates `gs://meshek-prod-models` (me-west1, uniform bucket-level access, versioning ON, 90-day non-current lifecycle) and grants `roles/storage.objectViewer` to `meshek-ml-run@meshek-prod.iam.gserviceaccount.com`. Uses the same `run` helper as the merchants bucket block so `DRY_RUN=1` works correctly.

- **`scripts/deploy-cloudrun.sh`** — two variable declarations (`MODELS_BUCKET`, `MODELS_MOUNT_PATH`) plus the second volume pair:
  - `--add-volume "name=models-vol,type=cloud-storage,bucket=${MODELS_BUCKET},readonly=true"`
  - `--add-volume-mount "volume=models-vol,mount-path=${MODELS_MOUNT_PATH}"`
  - `MESHEK_MODELS_DIR=/app/models` added to `ENV_VARS` (was missing despite D-08 claiming Phase 8.1 had set it).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 9-03-01 | Extend bootstrap-cloudrun.sh with models bucket + IAM | 315e60b | scripts/bootstrap-cloudrun.sh |
| 9-03-02 | Extend deploy-cloudrun.sh with second FUSE volume pair | c7ff25b | scripts/deploy-cloudrun.sh |
| 9-03-03 | Regression-check that merchants mount is untouched | (no-code) | — |

## Verification Results

All DRY_RUN checks passed:

```
DRY_RUN=1 bash scripts/bootstrap-cloudrun.sh | grep meshek-prod-models
==> Ensuring GCS bucket gs://meshek-prod-models in me-west1 (versioning on, 90d lifecycle)
+ gcloud storage buckets create gs://meshek-prod-models ...
+ gcloud storage buckets update gs://meshek-prod-models ... --versioning
+ gcloud storage buckets update gs://meshek-prod-models ... --lifecycle-file=...
==> Granting roles/storage.objectViewer on gs://meshek-prod-models ...
+ gcloud storage buckets add-iam-policy-binding ... --role=roles/storage.objectViewer
```

```
DRY_RUN=1 bash scripts/deploy-cloudrun.sh | grep 'models-vol\|merchants-vol'
... --add-volume name=merchants-vol,type=cloud-storage,bucket=meshek-prod-merchants
    --add-volume-mount volume=merchants-vol,mount-path=/var/lib/meshek/merchants
    --add-volume name=models-vol,type=cloud-storage,bucket=meshek-prod-models,readonly=true
    --add-volume-mount volume=models-vol,mount-path=/app/models ...
```

Existing test suite: **217 passed, 1 skipped** (D-24 regression — no regressions).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added MESHEK_MODELS_DIR to ENV_VARS in deploy-cloudrun.sh**
- **Found during:** Task 9-03-02, step 3 (grep check)
- **Issue:** D-08 stated "MESHEK_MODELS_DIR=/app/models already set in Phase 8.1 env vars" — grepping the file showed it was NOT present. The `load_model_bundle` traversal guard in `model_io.py` requires this env var for path validation; without it the service falls back to a CWD-relative `models/` root which would fail in the Cloud Run container.
- **Fix:** Added `ENV_VARS="${ENV_VARS},MESHEK_MODELS_DIR=/app/models"` after `MESHEK_MODEL_PATH` line.
- **Files modified:** scripts/deploy-cloudrun.sh
- **Commit:** c7ff25b

## Threat Surface Scan

No new network endpoints, auth paths, or file access patterns introduced. Both scripts are operator-only tooling (not service code). The `readonly=true` flag and `objectViewer` IAM role satisfy T-9-01 and T-9-02 mitigations from the plan's threat register.

## Known Stubs

None. Both scripts are complete operator tooling with no placeholder values.

## Self-Check: PASSED

- `scripts/bootstrap-cloudrun.sh` — exists, `bash -n` clean, DRY_RUN grep matched
- `scripts/deploy-cloudrun.sh` — exists, `bash -n` clean, both volume pair greps matched
- Commits 315e60b and c7ff25b present in git log
