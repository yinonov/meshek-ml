#!/usr/bin/env bash
# scripts/deploy-cloudrun.sh — D-26, D-06..D-24
# Routine deploy: Cloud Build submit + gcloud run deploy for meshek-ml.
#
#   ./scripts/deploy-cloudrun.sh                  # full deploy
#   DRY_RUN=1 ./scripts/deploy-cloudrun.sh        # print command, do not execute
#   ./scripts/deploy-cloudrun.sh --dry-run        # same
#   ./scripts/deploy-cloudrun.sh --project other-proj --region us-central1
#
# Requires: operator authenticated via `gcloud auth login`; bootstrap script
# must have been run once on the target project.

set -euo pipefail

PROJECT="${PROJECT:-meshek-prod}"
REGION="${REGION:-me-west1}"
SERVICE="${SERVICE:-meshek-ml}"
AR_REPO="me-west1-docker.pkg.dev/meshek-prod/meshek"
SA_EMAIL="meshek-ml-run@meshek-prod.iam.gserviceaccount.com"
BUCKET="meshek-prod-merchants"
MOUNT_PATH="/var/lib/meshek/merchants"
DRY_RUN="${DRY_RUN:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region)  REGION="$2";  shift 2 ;;
    --service) SERVICE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1;    shift ;;
    -h|--help)
      echo "Usage: $0 [--project P] [--region R] [--service S] [--dry-run]"
      exit 0 ;;
    *) echo "Unknown flag: $1" >&2; exit 2 ;;
  esac
done

GIT_SHA="$(git rev-parse --short HEAD)"
IMAGE="${AR_REPO}/${SERVICE}:${GIT_SHA}"

ENV_VARS="MESHEK_DATA_DIR=${MOUNT_PATH}"
ENV_VARS="${ENV_VARS},MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle"
ENV_VARS="${ENV_VARS},MESHEK_LOG_LEVEL=info"
ENV_VARS="${ENV_VARS},MESHEK_API_HOST=0.0.0.0"

emit() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '+ %s\n' "$*"
  else
    "$@"
  fi
}

echo "==> Building image ${IMAGE} via Cloud Build"
emit gcloud builds submit \
  --tag "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}"

echo "==> Deploying ${SERVICE} to Cloud Run (${REGION})"
emit gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT}" \
  --platform managed \
  --execution-environment=gen2 \
  --add-volume "name=merchants-vol,type=cloud-storage,bucket=${BUCKET}" \
  --add-volume-mount "volume=merchants-vol,mount-path=${MOUNT_PATH}" \
  --ingress internal-and-cloud-load-balancing \
  --no-allow-unauthenticated \
  --service-account "${SA_EMAIL}" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --concurrency 40 \
  --timeout 60 \
  --cpu-boost \
  --set-env-vars "${ENV_VARS}"

if [[ "${DRY_RUN}" != "1" ]]; then
  URL="$(gcloud run services describe "${SERVICE}" \
    --region "${REGION}" --project "${PROJECT}" \
    --format='value(status.url)')"
  echo "==> Deployed: ${URL}"
else
  echo "==> DRY_RUN=1 — no gcloud calls executed"
fi
