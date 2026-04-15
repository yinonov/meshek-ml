---
phase: 09-model-bundle-pipeline
plan: "04"
subsystem: docs
tags: [documentation, model-bundle, gcs, cloud-run, operator-runbook]
dependency_graph:
  requires: [09-01, 09-02, 09-03]
  provides: [operator-runbook-extended]
  affects: [docs/deploy-cloudrun.md]
tech_stack:
  added: []
  patterns: [gcs-versioning, cloud-run-fuse-mount, copy-in-place-rollback]
key_files:
  created: []
  modified:
    - docs/deploy-cloudrun.md
decisions:
  - "Placed new section as §9 (after existing §8 Known Limitations) to maintain the established numbered-section convention."
  - "Documented copy-in-place rollback explicitly citing Pitfall 5 from research to prevent operator error with gcloud storage restore."
  - "Complete rollback flow = 9.6 copy-in-place + 9.7 no-op revision bump presented as a pair so neither step is forgotten."
metrics:
  duration_minutes: 8
  completed_date: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 1
  lines_added: 171
---

# Phase 9 Plan 4: Operator Runbook — Training and Publishing Model Bundle Summary

**One-liner:** Extended `docs/deploy-cloudrun.md` with a self-contained §9 covering bootstrap → train → deploy → verify flow, LOCAL_ONLY/DRY_RUN modes, GCS generation inspection, #GENERATION copy-in-place rollback + no-op revision bump, and objectViewer read-only rationale.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 9-04-01 | Add "Training and publishing a model bundle" section | 1bc3929 | docs/deploy-cloudrun.md |
| 9-04-02 | Ensure rollback via generation-pin is documented | 1bc3929 | docs/deploy-cloudrun.md (regression guard — already complete from 9-04-01) |

## What Was Built

Section 9 of `docs/deploy-cloudrun.md` covers eight subsections:

1. **§9.1 Prerequisites** — authenticated gcloud with write on `gs://meshek-prod-models`, `.venv` activated, bootstrap run at least once.
2. **§9.2 Three-command flow (D-18)** — bootstrap → train-and-publish-model.sh → deploy-cloudrun.sh; expected outcome: `/health` 200 with `model_loaded: true`, `/recommend` returns `reasoning_tier: "ml_forecast"`.
3. **§9.3 Reproducibility (D-11)** — default seed=42, 20 merchants, 180 days; feature_cols and residual_std match to ≤1e-6 on re-run; enforced by `test_deterministic_rerun`.
4. **§9.4 Local / dry-run modes (D-13)** — `LOCAL_ONLY=1` trains without uploading; `DRY_RUN=1` prints the gcloud cp command without executing.
5. **§9.5 Inspecting GCS generations** — `gcloud storage objects list --all-versions --format='table(generation,timeCreated,size)'`; 90-day non-current retention (D-03).
6. **§9.6 Rollback (D-22)** — `gcloud storage cp "gs://meshek-prod-models/lightgbm_v1.bundle#${PRIOR_GENERATION}" gs://meshek-prod-models/lightgbm_v1.bundle --cache-control=no-cache`; explicit warning that `gcloud storage restore` does NOT apply (Pitfall 5).
7. **§9.7 Forcing a model refresh (D-19)** — `gcloud run services update meshek-ml --region me-west1 --project meshek-prod`; paired with §9.6 as the complete rollback flow.
8. **§9.8 Why objectViewer (D-23)** — service account read-only by design; `readonly=true` FUSE mount is defense-in-depth; cites T-9-01.

## Deviations from Plan

None — plan executed exactly as written. Task 9-04-02 was a regression guard that confirmed 9-04-01 already included the `#GENERATION` syntax and `gcloud run services update` in code blocks.

## Verification

All automated grep checks pass:

```
grep -qE 'Training and publishing'        docs/deploy-cloudrun.md  ✓
grep -qE 'train-and-publish-model\.sh'   docs/deploy-cloudrun.md  ✓
grep -qE 'LOCAL_ONLY|DRY_RUN'            docs/deploy-cloudrun.md  ✓
grep -qE 'objectViewer'                  docs/deploy-cloudrun.md  ✓
grep -qE 'generation|#[0-9]+'            docs/deploy-cloudrun.md  ✓
grep -qE 'gcloud run services update'    docs/deploy-cloudrun.md  ✓
```

## Known Stubs

None. This plan is documentation-only; all commands reference real scripts and buckets from Plans 09-01..09-03.

## Threat Flags

None. The new section documents existing infrastructure (bucket name and SA email already appear in bootstrap/deploy scripts in the repo). Per T-9-04-02 (accepted), these are gated by GCP IAM and are not secrets.

## Self-Check: PASSED

- `docs/deploy-cloudrun.md` exists and contains §9: FOUND
- Commit 1bc3929 exists: FOUND
- All six grep checks: PASSED
