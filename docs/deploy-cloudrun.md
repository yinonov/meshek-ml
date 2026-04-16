# meshek-ml Cloud Run Deployment Runbook

Operator guide for deploying, operating, and recovering the `meshek-ml`
inference service on Google Cloud Run in the `meshek-prod` project.

This runbook is self-contained. For the underlying flag rationale, see the
header comments in `scripts/bootstrap-cloudrun.sh` and
`scripts/deploy-cloudrun.sh`. Those scripts are the source of truth for flags;
this doc explains *when* and *why* to run them.

---

## 1. Prerequisites

Before running any command below, confirm:

- **gcloud SDK installed and authenticated:**
  ```bash
  gcloud auth login
  gcloud config set project meshek-prod
  ```
- **Operator IAM role on `meshek-prod`:** Project Owner, OR the combined set:
  `serviceusage.admin` + `artifactregistry.admin` + `storage.admin` +
  `iam.serviceAccountAdmin` + `resourcemanager.projectIamAdmin`.
  (Owner is simpler for bootstrapping; narrow roles are listed in
  `scripts/bootstrap-cloudrun.sh` header for least-privilege operators.)
- **Billing enabled** on `meshek-prod`.
- **Git working tree is clean** (deploy script embeds the git short SHA as the
  image tag; a dirty tree means the tag does not uniquely identify what was
  deployed):
  ```bash
  git status
  ```
- **Python virtual environment** activated (only needed for the smoke test):
  ```bash
  uv venv && uv sync          # first time
  source .venv/bin/activate   # subsequent runs
  ```

---

## 2. One-Time Bootstrap

Run **once** per GCP project. Safe to rerun — all steps are idempotent.

```bash
./scripts/bootstrap-cloudrun.sh
```

Or with explicit overrides (defaults are `meshek-prod` / `me-west1`):

```bash
./scripts/bootstrap-cloudrun.sh --project meshek-prod --region me-west1
```

To preview what the script will do without executing anything:

```bash
DRY_RUN=1 ./scripts/bootstrap-cloudrun.sh
# or: ./scripts/bootstrap-cloudrun.sh --dry-run
```

What bootstrap creates:

| Resource | Name |
|----------|------|
| Artifact Registry repo | `me-west1-docker.pkg.dev/meshek-prod/meshek` |
| GCS bucket | `gs://meshek-prod-merchants` (single-region `me-west1`, versioning on, 30-day lifecycle for non-current versions) |
| Service account | `meshek-ml-run@meshek-prod.iam.gserviceaccount.com` |
| Bucket IAM binding | `roles/storage.objectUser` granted to the service account above |

The GCS bucket persists per-merchant SQLite files across container restarts via
GCS FUSE. Bucket versioning provides a soft backup; the 30-day lifecycle keeps
storage costs bounded.

---

## 3. Routine Deploy

After bootstrap is done (once), every subsequent release is a single command:

```bash
./scripts/deploy-cloudrun.sh
```

With explicit project / region / service name overrides:

```bash
./scripts/deploy-cloudrun.sh --project meshek-prod --region me-west1 --service meshek-ml
```

**Pre-flight dry run** — prints the exact `gcloud` commands that would be
executed, without contacting GCP:

```bash
DRY_RUN=1 ./scripts/deploy-cloudrun.sh
# or: ./scripts/deploy-cloudrun.sh --dry-run
```

Use the dry-run output to verify the image tag (git short SHA), env vars, and
Cloud Run flags before committing to a real deploy.

What the script does:

1. Tags the image `me-west1-docker.pkg.dev/meshek-prod/meshek/meshek-ml:<git-sha>`
2. Builds the image via `gcloud builds submit` (Cloud Build — no local Docker
   daemon or push auth required)
3. Deploys to Cloud Run with:
   - GCS FUSE volume mount at `/var/lib/meshek/merchants`
   - `--ingress internal-and-cloud-load-balancing` (no public internet access)
   - `--no-allow-unauthenticated`
   - 512 MiB RAM, 1 vCPU, concurrency 40, timeout 60 s
   - `min-instances=0` (scale-to-zero), `max-instances=2`
   - Startup CPU boost (shortens cold-start while LightGBM loads)
4. Prints the deployed service URL when complete

Expected output ends with:

```
==> Deployed: https://meshek-ml-<hash>-ew.a.run.app
```

> **Note:** The `*.run.app` URL is not reachable from the public internet
> (internal ingress). Use `gcloud run services proxy` for direct access — see
> Section 4.

---

## 4. Smoke Test Against Deployed URL

The service uses internal ingress, so `curl https://meshek-ml-*.run.app` from
your laptop will be refused. Use `gcloud run services proxy` to tunnel through
your gcloud IAM identity without opening the service publicly.

**Terminal 1 — start the IAM proxy:**

```bash
gcloud run services proxy meshek-ml \
  --region me-west1 \
  --project meshek-prod
```

The proxy binds `http://localhost:8080` by default and runs in the foreground.
Keep it open.

**Terminal 2 — run the smoke test:**

```bash
MESHEK_CLOUDRUN_SMOKE=1 \
MESHEK_CLOUDRUN_URL=http://localhost:8080 \
.venv/bin/python -m pytest tests/deploy/test_cloudrun_smoke.py -x -v
```

The smoke test covers the full merchant flow:

1. `POST /merchants {}` → 201 Created (returns `merchant_id`)
2. `POST /merchants/{mid}/sales {"text": "20 עגבניות, 5 מלפפונים"}` → 200 OK (Hebrew sales line parsed)
3. `POST /merchants/{mid}/recommend {}` → 200 OK (recommendation list returned)

The test is guarded by `MESHEK_CLOUDRUN_SMOKE=1` so it never runs in normal
`uv run pytest` or CI passes.

Stop Terminal 1 (Ctrl-C) when done.

---

## 5. Rollback

To instantly shift 100% of traffic to the previous revision (no image rebuild):

```bash
gcloud run services update-traffic meshek-ml \
  --to-revisions=PREVIOUS=100 \
  --region me-west1 \
  --project meshek-prod
```

This is atomic — Cloud Run switches traffic at the router level. The current
bad revision stays deployed but receives 0% traffic.

To roll back to a specific older revision, first list available revisions:

```bash
gcloud run revisions list \
  --service meshek-ml \
  --region me-west1 \
  --project meshek-prod
```

Then pin traffic to that revision by name:

```bash
gcloud run services update-traffic meshek-ml \
  --to-revisions=meshek-ml-00005-xyz=100 \
  --region me-west1 \
  --project meshek-prod
```

After rollback, verify with the smoke test (Section 4) before declaring the
incident resolved.

---

## 6. Tail Logs / Debug

**Read recent logs (last 100 lines):**

```bash
gcloud run services logs read meshek-ml \
  --region me-west1 \
  --project meshek-prod \
  --limit 100
```

**Stream logs in real time:**

```bash
gcloud run services logs tail meshek-ml \
  --region me-west1 \
  --project meshek-prod
```

Logs are JSON-structured (from Phase 8's `JSONFormatter`). Cloud Logging
auto-detects the `severity` field and colors/filters entries accordingly.

**Logs Explorer** — for richer filtering and time-range queries, open
[Cloud Logging](https://console.cloud.google.com/logs/query) and use this
filter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="meshek-ml"
```

Useful filter additions:

```
# Only errors
severity>=ERROR

# Specific request_id (from API response header)
jsonPayload.request_id="<request-id>"
```

---

## 7. Cost Expectations

| Component | Billing model | Expected cost at 50 merchants |
|-----------|--------------|-------------------------------|
| Cloud Run compute | Per vCPU-second + per GiB-second; free tier: 360k vCPU-s/mo + 180k GiB-s/mo | ~1500 req/mo at ~50ms each = ~75 vCPU-s/mo — **well under free tier** |
| Cloud Run requests | Free tier: 2M req/mo | ~1500 req/mo — **free tier** |
| Idle cost | `min-instances=0` → scale-to-zero | **$0 when idle** |
| GCS FUSE bucket | Per GB stored + per-operation charges | 50 merchants × ~10 MB/SQLite = ~0.5 GB → **< $1/mo** |
| Cloud Build | First 120 min/day free; each deploy ~3 min | ~40 deploys/month = 120 min → **free tier** |

At typical greengrocer usage (~1 ordering request per merchant per day, 50
merchants), the entire Cloud Run stack fits comfortably within GCP's free tier.
Costs become non-trivial only if merchant count exceeds ~500 or if deploys
exceed ~40/day.

---

## 8. Known Limitations

### SQLite journal mode is DELETE (not WAL)

GCS FUSE does not implement POSIX file locking correctly. SQLite's default
WAL mode (`journal_mode=WAL`) relies on memory-mapped I/O and atomic rename
semantics that FUSE over object storage cannot guarantee — enabling WAL on
GCS FUSE risks database corruption.

Phase 8.1 forces `PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;` on
every store connection (D-10, D-11) as the safe workaround. DELETE journal
mode is single-writer and slower than WAL but safe on FUSE.

If any of the following occur, migrate to Cloud SQL Postgres:
- Merchant count grows past ~50 (pooled-prior scan becomes O(N) disk I/O)
- Cross-merchant aggregations or admin dashboards are needed
- GCS FUSE causes a production incident (corruption, lost writes, lock errors)

Migration path: [SEED-001](../.planning/seeds/SEED-001-gcp-native-storage-migration.md)

### max-instances=2

Intentional cap for v1.1. Do not raise without first verifying GCS FUSE
concurrent-writer behaviour. Each instance opens its own per-merchant SQLite
file per request, so concurrent requests for *different* merchants across
instances are fine. Concurrent writes to the *same merchant file* from
different instances will serialize via SQLite file locking — which GCS FUSE
approximates but does not fully honor.

### Internal ingress only

The `*.run.app` URL is not reachable from the public internet. Only the meshek
dashboard service account (bound via `roles/run.invoker`) or
`gcloud run services proxy` (Section 4) can call the service. This is
intentional (D-20, D-21).

### No custom domain

The service is accessed via the `run.app` URL generated by Cloud Run. Custom
domain setup is deferred (D-39) — the internal-only ingress makes it
unnecessary for v1.1.

### No CI/CD

Deploys are manual `./scripts/deploy-cloudrun.sh` invocations. Automated
Cloud Build triggers are deferred to a future milestone (D-37).

### Fly.io is preserved as a fallback

`fly.toml` is kept in the repository and is not deprecated by Phase 8.1.
Cloud Run is the primary production target; Fly.io remains a documented
fallback if Cloud Run has an availability issue in `me-west1`.

---

## 9. Training and publishing a model bundle

This section covers the offline model training workflow: how to train a
LightGBM bundle from synthetic seed data, publish it to GCS, and confirm
the live service picks it up. A new engineer should be able to complete
the end-to-end flow in under 5 minutes with only this section open.

### 9.1 Prerequisites

Before running the training workflow, confirm:

- **Authenticated `gcloud`** as an operator principal with write access on
  `gs://meshek-prod-models` (project owner, or a principal with
  `roles/storage.objectUser` on that bucket).
- **`.venv` activated** so `python -m meshek_ml.recommendation.cli_train`
  is importable:
  ```bash
  source .venv/bin/activate
  ```
- **`./scripts/bootstrap-cloudrun.sh` has been run at least once** on the
  target project. Bootstrap creates `gs://meshek-prod-models` with
  versioning on and a 90-day non-current lifecycle rule (D-04). The
  bucket must exist before `train-and-publish-model.sh` can upload.

### 9.2 The three-command flow (D-18)

```bash
./scripts/bootstrap-cloudrun.sh          # one-time, idempotent (D-04)
./scripts/train-and-publish-model.sh     # train + upload to gs://meshek-prod-models
./scripts/deploy-cloudrun.sh             # redeploy with both FUSE mounts (D-06)
```

Expected outcome after the third command:

- `GET /health` returns 200 with `"model_loaded": true`.
- `POST /recommend` for a merchant with ≥14 days of seeded sales history
  returns `"reasoning_tier": "ml_forecast"` (Tier 3 ML inference).

### 9.3 Reproducibility expectations (D-11)

Running `train-and-publish-model.sh` twice with the same seed produces
bundles whose `feature_cols` list is byte-identical and whose `residual_std`
matches to within 1e-6. This is enforced by
`tests/recommendation/test_model_bundle.py::test_deterministic_rerun`.

Default training parameters:

| Env var | Default | Effect |
|---------|---------|--------|
| `MESHEK_TRAIN_SEED` | `42` | NumPy RNG seed for synthetic data generation |
| `MESHEK_TRAIN_N_MERCHANTS` | `20` | Number of synthetic merchants to simulate |
| `MESHEK_TRAIN_DAYS` | `180` | Days of sales history per merchant |

The seed is the only input that matters for reproducibility. Setting a
global `numpy.random.seed()` is not required — `run_simulation()` uses
`np.random.default_rng(seed)` which is independent of the legacy global.

### 9.4 Local / dry-run modes (D-13)

Use these modes to verify the training pipeline without committing to a
production upload.

**`LOCAL_ONLY=1` — train locally, skip GCS upload:**

```bash
LOCAL_ONLY=1 ./scripts/train-and-publish-model.sh
```

Trains the bundle and writes it to `models/lightgbm_v1.bundle` (or
`MESHEK_TRAIN_OUTPUT`). No GCS operations. Use for smoke tests before
committing to a production upload. The bundle is load-verified in place.

**`DRY_RUN=1` — print the upload command without executing it:**

```bash
DRY_RUN=1 ./scripts/train-and-publish-model.sh
```

Prints the exact `gcloud storage cp` command the script would run, then
exits 0. Use to preview the upload destination before a real run.

**Custom parameters:**

```bash
LOCAL_ONLY=1 MESHEK_TRAIN_N_MERCHANTS=5 MESHEK_TRAIN_DAYS=30 \
  ./scripts/train-and-publish-model.sh
```

### 9.5 Inspecting GCS generations

Each run of `train-and-publish-model.sh` creates a new object generation
in `gs://meshek-prod-models`. The previous generation is preserved for 90
days by the bucket lifecycle rule (D-03) — no manual action needed.

List all preserved versions of the bundle:

```bash
gcloud storage objects list "gs://meshek-prod-models/lightgbm_v1.bundle" \
  --all-versions \
  --format='table(generation,timeCreated,size)'
```

The script also prints the generation number immediately after upload:

```
==> Published generation: 1748123456789012
    Rollback hint: gs://meshek-prod-models/lightgbm_v1.bundle#1748123456789012
```

Keep this generation number handy if you may need to roll back.

### 9.6 Rolling back to a prior bundle (D-22)

To roll back the live model to an earlier generation, copy that generation
back as the live object (copy-in-place):

```bash
PRIOR_GENERATION=1748123456789012   # from the list command above
gcloud storage cp \
  "gs://meshek-prod-models/lightgbm_v1.bundle#${PRIOR_GENERATION}" \
  "gs://meshek-prod-models/lightgbm_v1.bundle" \
  --cache-control=no-cache
```

Then force a new Cloud Run revision to pick up the restored bundle (see
Section 9.7).

**Important:** `gcloud storage restore` does NOT work for this rollback
(Pitfall 5 from research). `gcloud storage restore` restores soft-deleted
objects, not historical generations. The copy-in-place above is the only
supported rollback path for versioned generations. Running it leaves the
prior generation intact — GCS versioning guarantees it.

### 9.7 Forcing a model refresh (D-19)

Cloud Run caches the GCS FUSE mount per revision. After uploading a new
bundle (or rolling back via Section 9.6), force a new revision with a
no-op update:

```bash
gcloud run services update meshek-ml \
  --region me-west1 \
  --project meshek-prod
```

No image rebuild required. The new revision cold-starts against the latest
generation in `gs://meshek-prod-models`.

**Complete rollback flow = copy-in-place (9.6) + no-op revision bump (9.7).**
Forgetting the revision bump is the most common operator mistake — the
FUSE mount caches the old generation until a new revision starts.

### 9.8 Why objectViewer and not objectUser (D-23)

The Cloud Run service account
(`meshek-ml-run@meshek-prod.iam.gserviceaccount.com`) is granted
`roles/storage.objectViewer` on `gs://meshek-prod-models` — read-only
access. This is intentional.

Training is an offline operator action that runs from your local workstation
using your own GCP credentials. The service never writes to the models
bucket. Combined with `readonly=true` on the GCS FUSE volume mount (D-07),
this is defense-in-depth: even a service bug that attempts to write to
`/app/models` will fail at the OS level before any GCS API call is made.
This directly addresses threat T-9-01 from the Phase 9 threat model —
an attacker with service code execution cannot corrupt the production model
bundle, because the service account lacks write permissions and the mount
is read-only.

---

## Known Caveats

### Python Version Skew: Local Training vs Cloud Run

| Environment | Python Version | Purpose |
|-------------|---------------|---------|
| Local / CI training | 3.13 | `scripts/train_model.py` generates LightGBM bundle |
| Cloud Run runtime | 3.12 | `Dockerfile` serves inference via FastAPI |

**Impact:** LightGBM model bundles are forward-compatible (trained on 3.13,
served on 3.12) because the serialised format is Python-version-agnostic
(Booster binary plus metadata with no version-specific bytecode).
No action is required unless a future dependency introduces version-specific
serialization protocols.

**Mitigation if needed:** Pin both environments to the same Python version by
updating the `Dockerfile` base image to `python:3.13-slim` when Cloud Run's
base image supports it, or pin local training to 3.12 via `pyenv local 3.12`.
