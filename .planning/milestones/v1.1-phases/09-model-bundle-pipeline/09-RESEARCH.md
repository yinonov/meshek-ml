# Phase 9: Model Bundle Pipeline - Research

**Researched:** 2026-04-15
**Domain:** LightGBM training pipeline, GCS versioned storage, Cloud Run multi-volume FUSE mounts
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Second GCS FUSE mount at `/app/models`, bucket `gs://meshek-prod-models`
- **D-02:** Model NOT baked into the Docker image
- **D-03:** Bucket `gs://meshek-prod-models`, region `me-west1`, versioning ON, 90-day non-current lifecycle
- **D-04:** Bucket creation handled by `scripts/bootstrap-cloudrun.sh` (idempotent)
- **D-05:** SA `meshek-ml-run@meshek-prod.iam.gserviceaccount.com` gets `roles/storage.objectViewer`
- **D-06:** Deploy script adds two new flags: `--add-volume name=models-vol,type=cloud-storage,bucket=meshek-prod-models,readonly=true` and `--add-volume-mount volume=models-vol,mount-path=/app/models`
- **D-07:** `readonly=true` on the models volume
- **D-08:** `MESHEK_MODELS_DIR=/app/models` already set in Phase 8.1 env vars
- **D-09:** New script `scripts/train-and-publish-model.sh` runs cli_train, verifies load, uploads, prints generation
- **D-10:** New thin CLI `src/meshek_ml/recommendation/cli_train.py`, wraps `train_and_save()`, uses synthetic data generator with seed, writes bundle, prints JSON summary
- **D-11:** Two runs with same seed must produce bundles with `feature_cols` and `residual_std` matching to <=1e-6
- **D-12:** Upload uses `gcloud storage cp --cache-control=no-cache`; no Python GCS client added
- **D-13:** `DRY_RUN=1` prints without uploading; `LOCAL_ONLY=1` trains but skips upload
- **D-14/D-15:** `tests/recommendation/test_model_bundle.py`, 5 merchants, 30 days, runs under 5s
- **D-16:** `lifespan.py` NOT touched
- **D-17:** Degraded-start path continues to work if FUSE mount missing
- **D-18:** Operator workflow: bootstrap -> train -> deploy -> verify
- **D-19:** No auto-reload; operator uploads + redeploys
- **D-24:** All existing Phase 8/8.1 tests must continue to pass
- **D-25:** Only new test: `test_model_bundle.py`
- **D-26:** Docker smoke test unchanged

### Claude's Discretion

- Exact LightGBM hyperparameters in the tiny test fixture
- Whether `cli_train.py` uses argparse or just env vars
- Whether the train script writes a sidecar metadata JSON
- Exact log messages in the train script

### Deferred Ideas (OUT OF SCOPE)

- Per-merchant model retraining (REC-05/v2)
- `POST /retrain/{merchant_id}` (REC-05/v2)
- Federated training (OPT-02/v2)
- Model registry / Trackio integration
- Automated canary deploys
- Training on real merchant data
- Model quality dashboards
- A/B testing two bundles
- Pinning generation numbers in deploy flags
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODEL-01 | Service starts in non-degraded mode (`/health` -> 200) with a LightGBM bundle loaded | GCS FUSE second mount at `/app/models` + existing `MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle` wiring satisfies this with zero service code changes |
| MODEL-02 | Model bundle is reproducibly trainable from synthetic seed data and uploadable to `gs://meshek-prod-models` via a single script | `run_simulation(seed=42)` + `train_and_save()` is end-to-end byte-identical on repeat runs; `gcloud storage cp --cache-control=no-cache` handles upload |
</phase_requirements>

---

## Summary

Phase 9 is an infrastructure-and-tooling phase, not a code-logic phase. The Python service is not modified -- only three artefacts are new: `src/meshek_ml/recommendation/cli_train.py` (thin CLI wrapper), `scripts/train-and-publish-model.sh` (bash orchestrator), and `tests/recommendation/test_model_bundle.py` (regression test). The remaining work is GCS bucket creation and two Cloud Run flag additions.

Key technical findings: (1) LightGBM + joblib on this codebase is provably byte-identical given the same input data -- verified in this session; (2) `run_simulation()` is the correct function name -- `generate_dataset()` does not exist in the codebase; (3) `readonly=true` in the `--add-volume` flag is the exact string as confirmed by official Cloud Run docs; (4) `gcloud storage cp` overwrites in place when versioning is ON, creating a new generation on each upload -- the previous generation is preserved automatically.

**Primary recommendation:** Implement in two waves -- Wave 1 creates the bucket/IAM/deploy-flag additions (infrastructure), Wave 2 delivers `cli_train.py` + `train-and-publish-model.sh` + the regression test (code).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightgbm | 4.6.0 | LightGBM model training | Already installed [VERIFIED: .venv inspection] |
| joblib | (transitive) | Model bundle serialisation | Already used by `model_io.py` [VERIFIED: codebase] |
| gcloud SDK | at `/usr/local/share/google-cloud-sdk` | Upload, bucket management | Already used in Phase 8.1 scripts [VERIFIED: `which gcloud`] |

### No New Dependencies

Phase 9 adds zero new Python packages and zero new system tools. All needed tools are already installed. [VERIFIED: codebase + venv]

---

## Architecture Patterns

### Recommended Project Structure (new files only)

```
src/meshek_ml/recommendation/
    cli_train.py                 # new: thin CLI wrapping train_and_save()

scripts/
    bootstrap-cloudrun.sh        # extend: add models bucket block
    deploy-cloudrun.sh           # extend: add second --add-volume pair
    train-and-publish-model.sh   # new: bash orchestrator

tests/recommendation/
    test_model_bundle.py         # new: regression test
```

### Pattern 1: Cloud Run Multi-Volume Mount

**What:** Two independent `--add-volume` / `--add-volume-mount` pairs on a single `gcloud run deploy`.

**Confirmed:** Official Cloud Run docs state "You can mount multiple buckets at different mount paths." [CITED: https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts]

Exact incantation for both volumes together:

```bash
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --platform managed \
  --execution-environment=gen2 \
  --add-volume "name=merchants-vol,type=cloud-storage,bucket=${MERCHANTS_BUCKET}" \
  --add-volume-mount "volume=merchants-vol,mount-path=${MERCHANTS_MOUNT_PATH}" \
  --add-volume "name=models-vol,type=cloud-storage,bucket=${MODELS_BUCKET},readonly=true" \
  --add-volume-mount "volume=models-vol,mount-path=/app/models" \
  # ... remaining flags unchanged
```

- `readonly=true` is the exact string [CITED: official docs]
- `--execution-environment=gen2` is already in the script (Phase 8.1 D-19)
- No `--container` selectors needed (single-container service)

### Pattern 2: Bootstrap Script Models Bucket Block

Idempotent block to append to `scripts/bootstrap-cloudrun.sh` before the final "Bootstrap complete" echo. Style matches the existing merchants bucket block exactly:

```bash
MODELS_BUCKET="meshek-prod-models"

echo "==> Ensuring GCS bucket gs://${MODELS_BUCKET} in ${REGION} (versioning on, 90d lifecycle)"
if ! gcloud storage buckets describe "gs://${MODELS_BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  run gcloud storage buckets create "gs://${MODELS_BUCKET}" \
    --location="${REGION}" \
    --project="${PROJECT}" \
    --uniform-bucket-level-access
  run gcloud storage buckets update "gs://${MODELS_BUCKET}" \
    --project="${PROJECT}" \
    --versioning
  MODELS_LIFECYCLE_JSON="$(mktemp)"
  cat >"${MODELS_LIFECYCLE_JSON}" <<'JSON'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"daysSinceNoncurrentTime": 90, "isLive": false}
    }
  ]
}
JSON
  run gcloud storage buckets update "gs://${MODELS_BUCKET}" \
    --project="${PROJECT}" \
    --lifecycle-file="${MODELS_LIFECYCLE_JSON}"
  rm -f "${MODELS_LIFECYCLE_JSON}"
else
  echo "    (exists)"
fi

echo "==> Granting roles/storage.objectViewer on gs://${MODELS_BUCKET} to ${SA_EMAIL}"
run gcloud storage buckets add-iam-policy-binding "gs://${MODELS_BUCKET}" \
  --project="${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectViewer"
```

Note: `roles/storage.objectViewer` not `objectUser` -- the service only reads the model bucket.

### Pattern 3: Deploy Script Extension (Exact Diff)

Add to the variables section (around line 20):

```bash
MODELS_BUCKET="meshek-prod-models"
MODELS_MOUNT_PATH="/app/models"
```

After the existing merchants volume pair in the `gcloud run deploy` block (after line 67), add:

```bash
  --add-volume "name=models-vol,type=cloud-storage,bucket=${MODELS_BUCKET},readonly=true" \
  --add-volume-mount "volume=models-vol,mount-path=${MODELS_MOUNT_PATH}" \
```

No other changes to `deploy-cloudrun.sh`.

### Pattern 4: train-and-publish-model.sh Skeleton

```bash
#!/usr/bin/env bash
# scripts/train-and-publish-model.sh
# Train a LightGBM model bundle from synthetic seed data and publish to GCS.
# D-09, D-12, D-13.
#
# Env vars (all optional):
#   MESHEK_TRAIN_SEED      (default: 42)
#   MESHEK_TRAIN_MERCHANTS (default: 20)
#   MESHEK_TRAIN_DAYS      (default: 180)
#   BUNDLE_PATH            (default: models/lightgbm_v1.bundle)
#   GCS_BUCKET             (default: meshek-prod-models)
#   DRY_RUN=1              Print gcloud cp command, do not upload
#   LOCAL_ONLY=1           Train and write bundle, skip GCS upload

set -euo pipefail

SEED="${MESHEK_TRAIN_SEED:-42}"
N_MERCHANTS="${MESHEK_TRAIN_MERCHANTS:-20}"
DAYS="${MESHEK_TRAIN_DAYS:-180}"
BUNDLE_PATH="${BUNDLE_PATH:-models/lightgbm_v1.bundle}"
GCS_BUCKET="${GCS_BUCKET:-meshek-prod-models}"
DRY_RUN="${DRY_RUN:-0}"
LOCAL_ONLY="${LOCAL_ONLY:-0}"

BUNDLE_DIR="$(dirname "${BUNDLE_PATH}")"
mkdir -p "${BUNDLE_DIR}"
export MESHEK_MODELS_DIR="$(cd "${BUNDLE_DIR}" && pwd)"

echo "==> Training model (seed=${SEED}, n_merchants=${N_MERCHANTS}, days=${DAYS})"
python -m meshek_ml.recommendation.cli_train \
  --seed "${SEED}" \
  --n-merchants "${N_MERCHANTS}" \
  --days "${DAYS}" \
  --output "${BUNDLE_PATH}"

echo "==> Verifying bundle loads cleanly"
python -c "
import os, sys
os.environ['MESHEK_MODELS_DIR'] = '${MESHEK_MODELS_DIR}'
from meshek_ml.recommendation.model_io import load_model_bundle
from pathlib import Path
b = load_model_bundle(Path('${BUNDLE_PATH}'))
assert b['feature_cols'], 'feature_cols empty'
assert b['residual_std'] > 0, 'residual_std not positive'
print('Bundle OK: feature_cols=%d residual_std=%.6f' % (len(b['feature_cols']), b['residual_std']))
"

if [[ "${LOCAL_ONLY}" == "1" ]]; then
  echo "==> LOCAL_ONLY=1 -- skipping GCS upload"
  exit 0
fi

GCS_DEST="gs://${GCS_BUCKET}/lightgbm_v1.bundle"
echo "==> Uploading bundle to ${GCS_DEST}"

if [[ "${DRY_RUN}" == "1" ]]; then
  printf '+ gcloud storage cp --cache-control=no-cache %s %s\n' "${BUNDLE_PATH}" "${GCS_DEST}"
  echo "==> DRY_RUN=1 -- no upload executed"
  exit 0
fi

gcloud storage cp --cache-control=no-cache "${BUNDLE_PATH}" "${GCS_DEST}"

GENERATION="$(gcloud storage objects list "${GCS_DEST}" \
  --format='value(generation)' 2>/dev/null | head -1)"
echo "==> Uploaded. GCS generation: ${GENERATION}"
echo "    Rollback: gcloud storage cp 'gs://${GCS_BUCKET}/lightgbm_v1.bundle#PRIOR_GEN' '${GCS_DEST}' --cache-control=no-cache"
```

### Pattern 5: cli_train.py Module

**CRITICAL FINDING:** `generate_dataset()` does NOT exist in the codebase. CONTEXT.md D-10 references it incorrectly. The real function is `run_simulation(n_merchants, start_date, end_date, seed)` from `meshek_ml.simulation.generator`. [VERIFIED: grep of all src/; generator.py source read]

The `days` parameter from D-10 must be converted: `end_date = start_date + timedelta(days=days - 1)`.

Full implementation:

```python
# src/meshek_ml/recommendation/cli_train.py
# CLI entry point for offline LightGBM training -- D-10.
#
# Usage:
#     python -m meshek_ml.recommendation.cli_train [options]
#
# MESHEK_MODELS_DIR must be set (or default CWD/models) before calling.
# The train-and-publish-model.sh wrapper handles this automatically.
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train and save a LightGBM model bundle.")
    p.add_argument("--seed", type=int,
                   default=int(os.environ.get("MESHEK_TRAIN_SEED", "42")))
    p.add_argument("--n-merchants", type=int,
                   default=int(os.environ.get("MESHEK_TRAIN_MERCHANTS", "20")))
    p.add_argument("--days", type=int,
                   default=int(os.environ.get("MESHEK_TRAIN_DAYS", "180")))
    p.add_argument("--output", type=Path,
                   default=Path(os.environ.get("BUNDLE_PATH", "models/lightgbm_v1.bundle")))
    p.add_argument("--start-date", type=str, default="2024-01-01")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # run_simulation has no 'days' param; convert days -> end_date
    start = date.fromisoformat(args.start_date)
    end = start + timedelta(days=args.days - 1)

    # Late imports: surfaces missing-package errors clearly
    from meshek_ml.simulation.generator import run_simulation
    from meshek_ml.recommendation.training import train_and_save

    data = run_simulation(
        n_merchants=args.n_merchants,
        start_date=args.start_date,
        end_date=end.isoformat(),
        seed=args.seed,
    )
    bundle = train_and_save(args.output, data)

    summary = {
        "bundle_path": str(args.output.resolve()),
        "residual_std": bundle["residual_std"],
        "feature_count": len(bundle["feature_cols"]),
        "row_count": len(data),
        "seed": args.seed,
        "n_merchants": args.n_merchants,
        "days": args.days,
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
```

Note: cli_train.py does NOT set `MESHEK_MODELS_DIR` -- the bash wrapper derives and exports it from `dirname(BUNDLE_PATH)`. This keeps the module pure and testable with `monkeypatch`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GCS versioning for model rollback | Custom tag objects | GCS native object versioning | Automatic; each `cp` creates a new generation [VERIFIED: gcloud docs] |
| Model determinism | Custom hash-seeding | `run_simulation(seed=42)` default LightGBM | Already byte-identical end-to-end [VERIFIED: tests b4, b5] |
| FUSE mount in Cloud Run | Custom startup downloader | `--add-volume type=cloud-storage` | GA feature, zero service code [CITED: cloud.google.com] |
| Bundle load verification in bash | Parse Python stdout | `python -c "load_model_bundle(...)"` inline | Reuses existing path-guarded loader |

**Key insight:** Every load-bearing mechanism already exists. Phase 9 is wiring and a thin CLI wrapper.

---

## Determinism Analysis

**Verdict: End-to-end byte-identical with same seed -- VERIFIED EMPIRICALLY.**

**Layer 1: Data generation.** `run_simulation(seed=42)` uses `np.random.default_rng(seed)`. Two independent calls with the same parameters produce bit-for-bit identical DataFrames. [VERIFIED: test b5]

**Layer 2: LightGBM training.** LightGBM 4.6.0 with `subsample=0.8`, `colsample_bytree=0.8` is deterministic on identical input data even without `random_state`. [VERIFIED: test b7] The existing `train_lightgbm()` does not pass `random_state` -- this is acceptable because determinism is guaranteed through the data seed. D-16 prohibits touching `training.py`.

**Layer 3: Serialisation.** `joblib.dump` produces byte-identical output for equal Python objects on the same Python/joblib versions. [VERIFIED: test b4 -- sha256 of two independently trained bundles matches]

**The only seed that matters is `seed` passed to `run_simulation()`.** Setting Python `random.seed()` or `np.random.seed()` globally is NOT required -- `run_simulation` uses the modern `np.random.default_rng(seed)` which is independent of the legacy global. [VERIFIED: tests b4, b5, b7]

**D-11 test strategy:** Call `train_and_save()` twice on the same seed fixture DataFrame; assert `feature_cols` list equality and `abs(residual_std_1 - residual_std_2) <= 1e-6`. No need to regenerate data twice. Empirical diff was 0.0. [VERIFIED: test b4]

---

## Regression Test Shape

**File:** `tests/recommendation/test_model_bundle.py`

Design notes:
- Fixture scope `function` -- fast enough (<1s with tiny params), avoids contamination
- Fast params override: `n_estimators=20, num_leaves=7` via patching `lgb.LGBMRegressor` in tree_models [VERIFIED: test b11 -- 0.629s total]
- 30-day window is sufficient for training rows [VERIFIED: test b9]
- Expected feature_cols (17 columns) verified empirically [VERIFIED: test b8]: `lag_1, lag_7, lag_14, lag_28, rolling_mean_7, rolling_std_7, rolling_mean_14, rolling_std_14, rolling_mean_28, rolling_std_28, day_of_week, day_of_month, month, week_of_year, is_weekend, sin_annual, cos_annual`

```python
# tests/recommendation/test_model_bundle.py
# Regression tests for the LightGBM model bundle pipeline -- D-14, D-15.
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from meshek_ml.recommendation.model_io import load_model_bundle
from meshek_ml.recommendation.training import train_and_save
from meshek_ml.simulation.generator import run_simulation

_FAST_PARAMS = {"n_estimators": 20, "num_leaves": 7, "verbose": -1}

_EXPECTED_FEATURE_COLS = [
    "lag_1", "lag_7", "lag_14", "lag_28",
    "rolling_mean_7", "rolling_std_7",
    "rolling_mean_14", "rolling_std_14",
    "rolling_mean_28", "rolling_std_28",
    "day_of_week", "day_of_month", "month", "week_of_year",
    "is_weekend", "sin_annual", "cos_annual",
]


def _patch_fast():
    import lightgbm as lgb
    return patch(
        "meshek_ml.forecasting.tree_models.lgb.LGBMRegressor",
        side_effect=lambda **kw: lgb.LGBMRegressor(**{**kw, **_FAST_PARAMS}),
    )


@pytest.fixture
def tiny_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    data = run_simulation(n_merchants=5, start_date="2024-01-01",
                          end_date="2024-01-30", seed=42)
    with _patch_fast():
        bundle = train_and_save(tmp_path / "lightgbm_v1.bundle", data)
    return bundle, tmp_path, data


def test_bundle_round_trips(tiny_bundle):
    bundle, tmp_path, _ = tiny_bundle
    loaded = load_model_bundle(tmp_path / "lightgbm_v1.bundle")
    assert set(loaded.keys()) == {"model", "residual_std", "feature_cols"}


def test_feature_cols_present(tiny_bundle):
    bundle, _, _ = tiny_bundle
    assert bundle["feature_cols"], "feature_cols must not be empty"
    assert bundle["feature_cols"] == _EXPECTED_FEATURE_COLS


def test_residual_std_positive(tiny_bundle):
    bundle, _, _ = tiny_bundle
    assert bundle["residual_std"] > 0


def test_predict_shape(tiny_bundle):
    import pandas as pd
    bundle, _, _ = tiny_bundle
    x = pd.DataFrame([{c: 0.0 for c in bundle["feature_cols"]}])
    arr = np.asarray(bundle["model"].predict(x))
    assert arr.shape == (1,)
    assert np.isfinite(arr[0])


def test_determinism(tmp_path, monkeypatch):
    monkeypatch.setenv("MESHEK_MODELS_DIR", str(tmp_path))
    data = run_simulation(n_merchants=5, start_date="2024-01-01",
                          end_date="2024-01-30", seed=42)
    with _patch_fast():
        b1 = train_and_save(tmp_path / "run1.bundle", data)
    with _patch_fast():
        b2 = train_and_save(tmp_path / "run2.bundle", data)
    assert b1["feature_cols"] == b2["feature_cols"]
    assert abs(b1["residual_std"] - b2["residual_std"]) <= 1e-6
```

---

## Common Pitfalls

### Pitfall 1: generate_dataset() Does Not Exist

**What goes wrong:** `ImportError: cannot import name 'generate_dataset'`
**Root cause:** CONTEXT.md D-10 references `generate_dataset(n_merchants, days, seed=...)` -- this function was never created. [VERIFIED: grep of all src/]
**Fix:** Import `run_simulation` from `meshek_ml.simulation.generator`. Convert `days` to `end_date = start_date + timedelta(days - 1)`.

### Pitfall 2: MESHEK_MODELS_DIR Not Set

**What goes wrong:** `ValueError: Model path ... is outside the allowed models root`
**Root cause:** `_models_root()` falls back to `Path("models").resolve()` (CWD-relative) when the env var is not set.
**Fix:** The bash wrapper must `export MESHEK_MODELS_DIR="$(cd "$(dirname BUNDLE_PATH)" && pwd)"` before calling Python.

### Pitfall 3: GCS FUSE Cold-Start Latency

**What goes wrong:** `/health` returns 503 for longer than expected after a cold start.
**Root cause:** GCS FUSE materialises the model bundle from GCS on first access, not at mount time.
**Mitigation:** `--cpu-boost` already in deploy script (Phase 8.1 D-18). Not a problem at v1.1 volumes.

### Pitfall 4: readonly=true -- Exact String

**What goes wrong:** Mount fails or mounts read-write.
**Root cause:** The Cloud Run API accepts only the lowercase string `readonly=true`. `True`, `read-only`, or bare `readonly` are all wrong. [CITED: official docs]
**Fix:** Use `readonly=true` exactly in the `--add-volume` flag.

### Pitfall 5: gcloud storage restore Is for Soft-Deleted Objects Only

**What goes wrong:** `ERROR: (gcloud.storage.objects) Invalid choice: 'restore'`
**Root cause:** `gcloud storage objects restore` does not exist; `gcloud storage restore` restores soft-deleted objects, not historical generations. [VERIFIED: local gcloud help]
**Fix:** To roll back to a prior bundle generation, copy it back as the live object:
```bash
gcloud storage cp "gs://meshek-prod-models/lightgbm_v1.bundle#PRIOR_GEN" \
  gs://meshek-prod-models/lightgbm_v1.bundle --cache-control=no-cache
```
Then force a no-op Cloud Run revision bump.

### Pitfall 6: Serialisation Format Stability Across Versions

**What goes wrong:** Bundle saved with one Python/joblib version may not load in an image built with a different version.
**Root cause:** joblib uses Python's native serialisation protocol; format is not guaranteed stable across major versions.
**Mitigation:** Retrain whenever the Docker image is rebuilt with a different Python or joblib version. Not an issue for v1.1.

### Pitfall 7: --add-volume-mount Name Must Match --add-volume Name

**What goes wrong:** `gcloud run deploy` error: `volume 'models-vol' not found`
**Root cause:** The `volume=NAME` in `--add-volume-mount` must exactly match the `name=NAME` in the corresponding `--add-volume`.
**Fix:** Keep pairs adjacent; use distinct names (`merchants-vol`, `models-vol`).

### Pitfall 8: GCS FUSE Does Not Support Random Writes

**What goes wrong:** Any service code path that tries to write to `/app/models` fails.
**Mitigation:** Already handled -- `readonly=true` makes this a hard OS-level failure.

---

## Code Examples

### Getting generation number after upload

```bash
# [VERIFIED: gcloud storage objects list --help]
GENERATION="$(gcloud storage objects list "gs://${GCS_BUCKET}/lightgbm_v1.bundle" \
  --format='value(generation)' 2>/dev/null | head -1)"
echo "GCS generation: ${GENERATION}"
```

### Rolling back to a prior model bundle generation

```bash
# [VERIFIED: gcloud storage cp --help semantics]
gcloud storage cp "gs://meshek-prod-models/lightgbm_v1.bundle#${PRIOR_GENERATION}" \
  gs://meshek-prod-models/lightgbm_v1.bundle \
  --cache-control=no-cache

# Force a new Cloud Run revision to pick up the restored bundle:
gcloud run services update meshek-ml --region me-west1 --project meshek-prod
```

### Listing all bundle versions

```bash
gcloud storage objects list "gs://meshek-prod-models/lightgbm_v1.bundle" \
  --all-versions \
  --format='table(generation,timeCreated,size)'
```

---

## Validation Architecture

`nyquist_validation: true` in `.planning/config.json` -- section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests -q --ignore=tests/deploy` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODEL-01 | `load_model_bundle` round-trips bundle cleanly | unit | `pytest tests/recommendation/test_model_bundle.py::test_bundle_round_trips -x` | Wave 0 |
| MODEL-01 | `/health` -> 200 with model loaded (live) | integration | `MESHEK_CLOUDRUN_SMOKE=1 pytest tests/deploy/test_cloudrun_smoke.py` | Exists (Phase 8.1) |
| MODEL-02 | Bundle reproducible: feature_cols + residual_std match on re-run | unit | `pytest tests/recommendation/test_model_bundle.py::test_determinism -x` | Wave 0 |
| MODEL-02 | feature_cols contains expected lag/rolling columns | unit | `pytest tests/recommendation/test_model_bundle.py::test_feature_cols_present -x` | Wave 0 |
| MODEL-02 | model.predict returns 1-element finite array | unit | `pytest tests/recommendation/test_model_bundle.py::test_predict_shape -x` | Wave 0 |
| MODEL-02 | residual_std > 0 | unit | `pytest tests/recommendation/test_model_bundle.py::test_residual_std_positive -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/recommendation/test_model_bundle.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests -q --ignore=tests/deploy`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/recommendation/test_model_bundle.py` -- covers MODEL-01 (bundle round-trip) and MODEL-02 (determinism, feature_cols, predict shape, residual_std)

No new conftest changes needed -- function-scoped monkeypatch pattern from existing tests is sufficient.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Training is offline operator action |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | `roles/storage.objectViewer` on models bucket (read-only SA); only operator GCP principals upload |
| V5 Input Validation | yes (partial) | `load_model_bundle` validates required keys; `_assert_within_root` enforces path traversal guard |
| V6 Cryptography | no | GCS at-rest encryption is default |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `MESHEK_MODEL_PATH` | Tampering | `_assert_within_root()` in `load_model_bundle` [VERIFIED: model_io.py] |
| Malicious bundle uploaded to GCS | Tampering | `readonly=true` FUSE mount; SA has `objectViewer` only (cannot write from service) |
| Model bundle corruption via FUSE write | Tampering | `readonly=true` makes this physically impossible |
| Deserialization of untrusted bundle | Tampering | Not mitigated at code level; acceptable for v1.1 (only operator GCP credentials can write to the bucket) |

---

## Open Questions

No blocking open questions. All 7 research items fully resolved.

**One non-blocking correction for the planner:** CONTEXT.md D-10 references `generate_dataset(n_merchants, days, seed=...)` -- this function does not exist. Implementer must use `run_simulation(n_merchants, start_date, end_date, seed)` and convert `days` to `end_date = start_date + timedelta(days - 1)`. [VERIFIED: grep of all src/]

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| gcloud SDK | bootstrap/deploy/train scripts | yes | `/usr/local/share/google-cloud-sdk` | -- |
| lightgbm | training | yes | 4.6.0 | -- |
| joblib | model_io | yes | (transitive) | -- |
| Python | cli_train.py | yes | 3.13.5 local / 3.12 in image | -- |
| pytest | test_model_bundle.py | yes | 9.0.2 | -- |
| GCS bucket gs://meshek-prod-models | train+publish, FUSE mount | NOT YET CREATED | -- | Created by bootstrap (Wave 1 prerequisite) |
| Cloud Run service meshek-ml | live MODEL-01 verification | yes | revision meshek-ml-00001-mln | -- |

**Missing dependencies with no fallback:**
- `gs://meshek-prod-models` bucket must be created by `./scripts/bootstrap-cloudrun.sh` before training or deployment

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `gcloud storage objects list gs://BUCKET/file --format='value(generation)'` returns the current live generation number | Code Examples | Generation print shows wrong value; low risk, easily tested before use |
| A2 | `gcloud run services update` without image change bumps the revision and refreshes the FUSE mount | Patterns | Rollback workflow might need specifying a new image tag; low risk [ASSUMED] |

All other claims are VERIFIED or CITED.

---

## Sources

### Primary (HIGH confidence)

- Codebase: `src/meshek_ml/simulation/generator.py` -- `run_simulation` signature [VERIFIED]
- Codebase: `src/meshek_ml/recommendation/training.py` -- `train_and_save` signature [VERIFIED]
- Codebase: `src/meshek_ml/recommendation/model_io.py` -- traversal guard [VERIFIED]
- Codebase: `src/meshek_ml/forecasting/tree_models.py` -- `train_lightgbm`, default params [VERIFIED]
- Codebase: `scripts/deploy-cloudrun.sh` -- existing volume flag pattern [VERIFIED]
- Codebase: `scripts/bootstrap-cloudrun.sh` -- existing bucket creation pattern [VERIFIED]
- Empirical: determinism end-to-end, tests b4 b5 b7 [VERIFIED: Python REPL]
- Empirical: 30-day fixture produces training rows, test b9 [VERIFIED]
- Empirical: fast params keep test under 1s, test b11 [VERIFIED]
- Empirical: feature_cols list of 17 columns, test b8 [VERIFIED]
- Cloud Run GCS FUSE docs: readonly=true syntax, multi-volume support [CITED: https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts]

### Secondary (MEDIUM confidence)

- `gcloud storage cp --help` -- `--cache-control` flag confirmed [VERIFIED: local gcloud]
- `gcloud storage restore --help` -- soft-delete semantics confirmed [VERIFIED: local gcloud]

### Tertiary (LOW confidence)

- A2: `gcloud run services update` refreshes FUSE mount [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries verified in venv
- Architecture: HIGH -- patterns derived from existing scripts + empirical tests
- Pitfalls: HIGH -- VERIFIED empirically or from official docs
- Determinism: HIGH -- byte-identical end-to-end in three independent experiments

**Research date:** 2026-04-15
**Valid until:** 2026-07-15 (stable domain; Cloud Run FUSE API is GA)

---

## RESEARCH COMPLETE
