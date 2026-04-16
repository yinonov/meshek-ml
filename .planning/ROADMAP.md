# Roadmap: meshek-ml

## Milestones

- **v1.0 Evidence-Based Colab Pipeline** — Phases 1-4 (shipped 2026-03-31)
- **v1.1 Merchant Order Advisor** — Phases 5-8 (in progress)

## Phases

<details>
<summary>v1.0 Evidence-Based Colab Pipeline (Phases 1-4) — SHIPPED 2026-03-31</summary>

- [x] Phase 1: Approach & Colab Bootstrap (2/2 plans) — completed 2026-03-31
- [x] Phase 2: Forecasting Pipeline (2/2 plans) — completed 2026-03-31
- [x] Phase 3: Optimization Baseline (1/1 plans) — completed 2026-03-31
- [x] Phase 4: Integration & Documentation (1/1 plans) — completed 2026-03-31

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### v1.1 Merchant Order Advisor (In Progress)

**Milestone Goal:** Expose the existing forecast + optimization pipeline as an ML inference service that the meshek app consumes to deliver daily order recommendations.

- [x] **Phase 5: Data Foundation** - Per-merchant SQLite storage, schemas, and merchant profile management ✓
- [x] **Phase 6: Recommendation Engine** - Three-tier cold-start recommendation logic with LightGBM startup load ✓
- [x] **Phase 7: Hebrew Input Parsing** - Dictionary-based Hebrew product name and quantity parsing ✓
- [x] **Phase 8: API Surface & Deployment** - FastAPI endpoints wired end-to-end, Docker container for deployment (completed 2026-04-14)

## Phase Details

### Phase 5: Data Foundation
**Goal**: Per-merchant sales history and profiles can be stored and retrieved in isolated SQLite files
**Depends on**: Phase 4 (v1.0 shipped codebase)
**Requirements**: STOR-01, STOR-02
**Success Criteria** (what must be TRUE):
  1. Sales records for merchant A are stored in a separate SQLite file from merchant B — isolation is filesystem-level
  2. A new merchant profile can be created and retrieved with zero configuration required
  3. Daily sales records can be written and read back with all fields intact
  4. The storage layer enforces the canonical schema (date, merchant_id, product, quantity) with fail-fast errors
**Plans**: TBD

### Phase 6: Recommendation Engine
**Goal**: The service can produce a confidence-scored order recommendation for any merchant regardless of how much history they have
**Depends on**: Phase 5
**Requirements**: REC-01, REC-02, REC-03, REC-04, INFRA-01
**Success Criteria** (what must be TRUE):
  1. A merchant with zero sales history receives a recommendation based on product category defaults (Tier 1) rather than an error
  2. A merchant with fewer than 14 days of history receives a recommendation using cross-merchant pooled priors (Tier 2)
  3. A merchant with 14 or more days of history receives a LightGBM-forecasted recommendation (Tier 3)
  4. Every recommendation response includes a `reasoning_tier` field and a `confidence_score` field
  5. The LightGBM model is loaded once at service startup via FastAPI lifespan — not on each request
**Plans:** 4 plans
Plans:
- [x] 06-01-PLAN.md — Wave 1: contracts, configs, schemas, service extra, public storage helper
- [x] 06-02-PLAN.md — Wave 2: Tier 1 category defaults + Tier 2 pooled priors + PooledStore
- [x] 06-03-PLAN.md — Wave 3: LightGBM train_and_save + safe model_io + Tier 3 inference
- [x] 06-04-PLAN.md — Wave 4: RecommendationEngine façade + FastAPI lifespan factory + e2e tests

### Phase 7: Hebrew Input Parsing
**Goal**: Free-text Hebrew sales input is reliably mapped to canonical product IDs and quantities before being stored
**Depends on**: Phase 5
**Requirements**: PARSE-01, PARSE-02
**Success Criteria** (what must be TRUE):
  1. Hebrew product names including singular and plural forms and common misspellings are resolved to the correct canonical product ID
  2. A quantity and unit can be extracted from Hebrew free text regardless of whether the number precedes or follows the product name (e.g., "20 עגבניות" and "עגבניות 20" both parse correctly)
  3. An unrecognised Hebrew string returns a structured parse error rather than silently producing a wrong product ID
**Plans:** 4 plans
Plans:
- [x] 07-01-PLAN.md — Wave 1: parsing.normalize (Unit enum, niqqud strip, final-letter fold, unit aliases)
- [x] 07-02-PLAN.md — Wave 2: parsing.catalog + configs/parsing/products_he.yaml seed (~30 products)
- [x] 07-03-PLAN.md — Wave 3: parsing.parser (ParsedSale, ParseError, order-invariant parse_sales_line)
- [x] 07-04-PLAN.md — Wave 4: public package API + D-18 integration tests against real seed catalog

### Phase 8: API Surface & Deployment
**Goal**: The meshek app can call all four endpoints over HTTP and the service can be deployed as a Docker container
**Depends on**: Phase 6, Phase 7
**Requirements**: API-01, API-02, API-03, API-04, INFRA-02
**Success Criteria** (what must be TRUE):
  1. `GET /health` returns a 200 response confirming the service is alive and the model is loaded
  2. `POST /merchants` creates a new merchant with zero required configuration and returns the merchant ID
  3. `POST /sales` accepts a daily sales record (including Hebrew free-text input via the parser) and stores it successfully
  4. `POST /recommend` returns per-product order quantities with reasoning tier and confidence score for any merchant
  5. The service starts and handles requests correctly inside a Docker container deployable to Railway or Fly.io
**UI hint**: no
**Plans:** 6/6 plans complete
Plans:
- [x] 08-01-PLAN.md — Wave 1: create_app factory + /health (+ Wave 0 scaffolding, uvicorn/lightgbm deps, degraded-start contract)
- [x] 08-02-PLAN.md — Wave 1: POST /merchants (regex-validated merchant_id, auto-uuid4 id)
- [x] 08-03-PLAN.md — Wave 2: POST /sales (structured items + Hebrew free-text partial-success)
- [x] 08-04-PLAN.md — Wave 2: POST /recommend (lifespan-cached engine, all three tiers)
- [x] 08-05-PLAN.md — Wave 3: central exception handlers + error envelope + structured JSON request logs
- [x] 08-06-PLAN.md — Wave 3: Dockerfile + .dockerignore + fly.toml + env-guarded Docker smoke test

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Approach & Colab Bootstrap | v1.0 | 2/2 | Complete | 2026-03-31 |
| 2. Forecasting Pipeline | v1.0 | 2/2 | Complete | 2026-03-31 |
| 3. Optimization Baseline | v1.0 | 1/1 | Complete | 2026-03-31 |
| 4. Integration & Documentation | v1.0 | 1/1 | Complete | 2026-03-31 |
| 5. Data Foundation | v1.1 | 0/? | Not started | - |
| 6. Recommendation Engine | v1.1 | 0/? | Not started | - |
| 7. Hebrew Input Parsing | v1.1 | 4/4 | Complete | 2026-04-14 |
| 8. API Surface & Deployment | v1.1 | 6/6 | Complete   | 2026-04-14 |

### Phase 8.1: Cloud Run Deployment (INSERTED)
**Goal**: The meshek-ml service runs on Google Cloud Run in the existing `meshek-prod` GCP project with per-merchant SQLite files persisted across container restarts via a GCS FUSE mount, deployable with a single `gcloud` command.
**Depends on**: Phase 8
**Requirements**: INFRA-03
**Success Criteria** (what must be TRUE):
  1. `scripts/deploy-cloudrun.sh` deploys the image to Cloud Run in the `meshek-prod` project / `me-west1` region via Artifact Registry, returning a live URL
  2. A GCS bucket (`gs://meshek-prod-merchants` or equivalent) is mounted at `/var/lib/meshek/merchants` inside the Cloud Run container via the native GCS FUSE volume integration
  3. `MerchantStore` forces SQLite `journal_mode=DELETE` so FUSE incompatibilities with WAL mode cannot corrupt merchant databases
  4. `GET /health` on the deployed service URL returns 200 or 503 (degraded) within 30s of deployment
  5. A repeatable deploy smoke test (`tests/deploy/test_cloudrun_smoke.py`, guarded by `MESHEK_CLOUDRUN_SMOKE=1`) posts `/merchants` and `/sales` against the live URL and asserts 201/200
  6. `docs/deploy-cloudrun.md` documents the one-shot deploy path, env var wiring, and rollback

**Out of scope** (see SEED-001): Cloud SQL / Postgres migration, multi-region failover, IAM-based per-caller auth beyond `--ingress=internal`, CI/CD automation
**UI hint**: no

Plans:
- [x] TBD (run /gsd-plan-phase 8.1 to break down) (completed 2026-04-15)

### Phase 9: Model Bundle Pipeline
**Goal**: A LightGBM model bundle is reproducibly trainable from synthetic seed data via a single script, published to a versioned GCS location, and loaded by Cloud Run at startup so `/health` flips to 200 and Tier 3 ML-forecasted recommendations work end-to-end.
**Depends on**: Phase 8.1
**Requirements**: MODEL-01, MODEL-02
**Success Criteria** (what must be TRUE):
  1. `scripts/train-and-publish-model.sh` (or equivalent) trains a model via `meshek_ml.recommendation.training.train_and_save()` using deterministic seed data and produces `lightgbm_v1.bundle` reproducibly
  2. The same script uploads the bundle to `gs://meshek-prod-models/lightgbm_v1.bundle` (idempotent, versioned via GCS versioning + a `:latest` symlink object or generation pinning)
  3. Cloud Run loads the model at startup — either by mounting `gs://meshek-prod-models` as a second GCS FUSE volume at `/app/models` and pointing `MESHEK_MODEL_PATH` there, OR by downloading the bundle in a startup hook before the FastAPI lifespan reads it
  4. `GET /health` on the redeployed service returns **200** with `{model_loaded: true}` (no longer degraded)
  5. `POST /recommend` for a merchant with ≥14 days of seeded sales returns `reasoning_tier: "ml_forecast"` (Tier 3 path exercised end-to-end)
  6. A regression test (`tests/recommendation/test_model_bundle.py`) loads the bundle produced by the script and asserts `feature_cols`, `residual_std`, and `model.predict` shape
  7. `docs/deploy-cloudrun.md` updated with the train-and-publish step in the bootstrap section

**Out of scope** (deferred): per-merchant model retraining (REC-05/v2), federated training (OPT-02/v2), model registry / experiment tracking (Trackio is wired but not gated), async retrain endpoint
**UI hint**: no

Plans:
- [x] TBD (run /gsd-plan-phase 9 to break down) (completed 2026-04-15)

### Phase 10: Fix Cloud Run Smoke Test
**Goal**: The automated Cloud Run smoke test (`test_cloudrun_smoke.py`) calls the correct API paths and asserts the correct response fields, so the "Automated Cloud Run smoke" E2E flow passes without manual verification
**Depends on**: Phase 8.1
**Requirements**: INFRA-03
**Gap Closure:** Closes integration gap (Phase 8.1 -> Phase 8 URL mismatch) and flow gap ("Automated Cloud Run smoke" broken) from v1.1 audit
**Success Criteria** (what must be TRUE):
  1. `test_cloudrun_smoke.py` calls `POST /sales` with `merchant_id` in the request body (not `/merchants/{id}/sales`)
  2. `test_cloudrun_smoke.py` calls `POST /recommend` with `merchant_id` in the request body (not `/merchants/{id}/recommend`)
  3. Response assertions check for `accepted_rows` and `skipped` fields (not `parsed`)
  4. The smoke test passes when run against the live Cloud Run service with `MESHEK_CLOUDRUN_SMOKE=1`
**UI hint**: no
**Plans:** 1/1 plans complete
Plans:
- [x] 10-01-PLAN.md — Fix smoke test paths, payloads, and response assertions

### Phase 11: Milestone Documentation Cleanup
**Goal**: All v1.1 documentation artifacts accurately reflect the completed state — checkboxes checked, traceability current, SUMMARY frontmatter complete, and env skew documented
**Depends on**: Phase 9
**Requirements**: API-01, API-02, API-03, API-04, MODEL-01, MODEL-02
**Gap Closure:** Closes tech debt from v1.1 audit (unchecked boxes, missing frontmatter, stale counts, env skew)
**Success Criteria** (what must be TRUE):
  1. REQUIREMENTS.md checkboxes for API-01, API-02, API-03, API-04, MODEL-01, MODEL-02 are checked
  2. REQUIREMENTS.md traceability table shows all 17 requirements as `Complete` with coverage count `17/17`
  3. Phase 6 SUMMARY frontmatter includes `requirements_completed` listing REC-01..04, INFRA-01
  4. Phase 8 SUMMARY frontmatter includes `requirements_completed` listing API-01..04, INFRA-02
  5. Python env skew (3.13 local training vs 3.12 Cloud Run) is documented in `docs/deploy-cloudrun.md` as a known caveat
**UI hint**: no

Plans:
- [x] TBD (run /gsd-plan-phase 11 to break down) (completed 2026-04-16)
