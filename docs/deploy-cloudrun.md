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
