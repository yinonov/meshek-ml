#!/usr/bin/env bash
# scripts/bootstrap-cloudrun.sh — D-28, D-09, D-07, D-08
# One-time setup for Phase 8.1 Cloud Run deployment of meshek-ml.
# Idempotent: safe to rerun. No destructive operations.
#
# Requires: gcloud SDK authenticated as a principal with project owner OR the
# combined roles (serviceusage.admin + artifactregistry.admin + storage.admin +
# iam.serviceAccountAdmin + resourcemanager.projectIamAdmin) on meshek-prod.
#
# Usage:
#   ./scripts/bootstrap-cloudrun.sh
#   ./scripts/bootstrap-cloudrun.sh --project meshek-prod --region me-west1
#   DRY_RUN=1 ./scripts/bootstrap-cloudrun.sh
#   ./scripts/bootstrap-cloudrun.sh --dry-run

set -euo pipefail

PROJECT="${PROJECT:-meshek-prod}"
REGION="${REGION:-me-west1}"
AR_REPO_NAME="meshek"
BUCKET="meshek-prod-merchants"
SA_NAME="meshek-ml-run"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
DRY_RUN="${DRY_RUN:-0}"

# Flag parsing (--project, --region, --dry-run)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region)  REGION="$2";  shift 2 ;;
    --dry-run) DRY_RUN=1;    shift ;;
    -h|--help)
      echo "Usage: $0 [--project PROJECT] [--region REGION] [--dry-run]"
      exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

# Re-derive SA_EMAIL after flag parsing (PROJECT may have changed)
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

echo "==> Enabling required APIs on project ${PROJECT}"
run gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT}"

echo "==> Ensuring Artifact Registry repo ${AR_REPO_NAME} in ${REGION}"
if ! gcloud artifacts repositories describe "${AR_REPO_NAME}" \
      --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  run gcloud artifacts repositories create "${AR_REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}" \
    --project="${PROJECT}" \
    --description="meshek container images"
else
  echo "    (exists)"
fi

echo "==> Ensuring GCS bucket gs://${BUCKET} in ${REGION} (versioning on, 30d lifecycle)"
if ! gcloud storage buckets describe "gs://${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  run gcloud storage buckets create "gs://${BUCKET}" \
    --location="${REGION}" \
    --project="${PROJECT}" \
    --uniform-bucket-level-access
  run gcloud storage buckets update "gs://${BUCKET}" \
    --project="${PROJECT}" \
    --versioning
  # Lifecycle rule: delete non-current versions after 30 days
  LIFECYCLE_JSON="$(mktemp)"
  cat >"${LIFECYCLE_JSON}" <<'JSON'
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"daysSinceNoncurrentTime": 30, "isLive": false}
    }
  ]
}
JSON
  run gcloud storage buckets update "gs://${BUCKET}" \
    --project="${PROJECT}" \
    --lifecycle-file="${LIFECYCLE_JSON}"
  rm -f "${LIFECYCLE_JSON}"
else
  echo "    (exists)"
fi

echo "==> Ensuring service account ${SA_EMAIL}"
if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
  run gcloud iam service-accounts create "${SA_NAME}" \
    --project="${PROJECT}" \
    --display-name="meshek-ml Cloud Run runtime"
else
  echo "    (exists)"
fi

echo "==> Granting roles/storage.objectUser on gs://${BUCKET} to ${SA_EMAIL}"
run gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --project="${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectUser"

echo "==> Bootstrap complete."
