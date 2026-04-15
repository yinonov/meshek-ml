#!/usr/bin/env bash
# scripts/train-and-publish-model.sh — D-09, D-12, D-13
# Operator entrypoint: train a LightGBM bundle from synthetic seed data and
# publish it to GCS. Step 2 of the three-command operator workflow:
#   1. ./scripts/bootstrap-cloudrun.sh
#   2. ./scripts/train-and-publish-model.sh   <-- this script
#   3. ./scripts/deploy-cloudrun.sh
#
# Modes:
#   DRY_RUN=1   Print the gcloud storage cp command; skip upload. Exit 0.
#   LOCAL_ONLY=1  Train and write bundle to BUNDLE_PATH; skip GCS upload. Exit 0.
#   (neither)   Full mode: train, verify, upload, print generation number.
#
# Env vars (all have defaults):
#   MESHEK_TRAIN_SEED         Random seed for reproducible training (default: 42)
#   MESHEK_TRAIN_N_MERCHANTS  Synthetic merchant count (default: 20)
#   MESHEK_TRAIN_DAYS         Days of history to simulate (default: 180)
#   MESHEK_TRAIN_OUTPUT       Local bundle destination path (default: models/lightgbm_v1.bundle)
#   GCS_BUCKET                GCS bucket name for model artifacts (default: meshek-prod-models)
#   PYTHON                    Python interpreter (default: python)
#   DRY_RUN                   Set to 1 to print upload command without executing (default: 0)
#   LOCAL_ONLY                Set to 1 to skip GCS upload entirely (default: 0)
#
# Usage:
#   ./scripts/train-and-publish-model.sh
#   ./scripts/train-and-publish-model.sh --project meshek-prod --region me-west1
#   DRY_RUN=1 ./scripts/train-and-publish-model.sh
#   LOCAL_ONLY=1 MESHEK_TRAIN_N_MERCHANTS=5 MESHEK_TRAIN_DAYS=30 ./scripts/train-and-publish-model.sh

set -euo pipefail

# ---- Defaults -----------------------------------------------------------
SEED="${MESHEK_TRAIN_SEED:-42}"
N_MERCHANTS="${MESHEK_TRAIN_N_MERCHANTS:-20}"
DAYS="${MESHEK_TRAIN_DAYS:-180}"
BUNDLE_PATH="${MESHEK_TRAIN_OUTPUT:-models/lightgbm_v1.bundle}"
GCS_BUCKET="${GCS_BUCKET:-meshek-prod-models}"
PROJECT="${PROJECT:-meshek-prod}"
REGION="${REGION:-me-west1}"
DRY_RUN="${DRY_RUN:-0}"
LOCAL_ONLY="${LOCAL_ONLY:-0}"
PYTHON="${PYTHON:-python}"

# ---- Flag parser --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region)  REGION="$2";  shift 2 ;;
    --bucket)  GCS_BUCKET="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1;    shift ;;
    -h|--help)
      echo "Usage: $0 [--project P] [--region R] [--bucket B] [--dry-run]"
      exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

GCS_DEST="gs://${GCS_BUCKET}/lightgbm_v1.bundle"

# ---- DRY_RUN short-circuit (before any real work) -----------------------
if [[ "${DRY_RUN}" == "1" ]]; then
  printf '+ gcloud storage cp --cache-control=no-cache %s %s\n' "${BUNDLE_PATH}" "${GCS_DEST}"
  exit 0
fi

# ---- Step 1: Train -------------------------------------------------------
echo "==> Training model bundle (seed=${SEED}, n_merchants=${N_MERCHANTS}, days=${DAYS})"

# Resolve and create the bundle directory before invoking Python.
# This also exports MESHEK_MODELS_DIR so load_model_bundle's traversal guard
# (T-9-02-01) finds the right root — without it the relative_to() check fails.
mkdir -p "$(dirname "${BUNDLE_PATH}")"
export MESHEK_MODELS_DIR
MESHEK_MODELS_DIR="$(cd "$(dirname "${BUNDLE_PATH}")" && pwd)"

"${PYTHON}" -m meshek_ml.recommendation.cli_train \
  --seed "${SEED}" \
  --n-merchants "${N_MERCHANTS}" \
  --days "${DAYS}" \
  --output "${BUNDLE_PATH}"

# ---- Step 2: Load-verify ------------------------------------------------
echo "==> Verifying bundle loads cleanly from ${BUNDLE_PATH}"

"${PYTHON}" - <<PYEOF
import os, sys
from pathlib import Path

os.environ.setdefault("MESHEK_MODELS_DIR", "${MESHEK_MODELS_DIR}")

from meshek_ml.recommendation.model_io import load_model_bundle

bundle = load_model_bundle(Path("${BUNDLE_PATH}"))
assert bundle.get("feature_cols"), "load_model_bundle returned empty feature_cols"
assert bundle.get("residual_std", 0) > 0, "load_model_bundle returned residual_std <= 0"
n_features = len(bundle["feature_cols"])
rsd = bundle["residual_std"]
print(f"Bundle OK: {n_features} features, residual_std={rsd:.6f}")
PYEOF

# ---- Step 3: Upload or short-circuit ------------------------------------
if [[ "${LOCAL_ONLY}" == "1" ]]; then
  echo "LOCAL_ONLY=1 — skipping GCS upload"
  exit 0
fi

# Full mode: upload to GCS (D-12, --cache-control=no-cache required)
echo "==> Uploading ${BUNDLE_PATH} to ${GCS_DEST}"
gcloud storage cp --cache-control=no-cache "${BUNDLE_PATH}" "${GCS_DEST}"

# ---- Step 4: Print generation number for version pinning ---------------
GENERATION="$(gcloud storage objects describe "${GCS_DEST}" \
  --format='value(generation)')"

echo "==> Published generation: ${GENERATION}"
echo "    Rollback hint: gs://${GCS_BUCKET}/lightgbm_v1.bundle#${GENERATION}"
