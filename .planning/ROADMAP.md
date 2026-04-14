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
- [ ] **Phase 8: API Surface & Deployment** - FastAPI endpoints wired end-to-end, Docker container for deployment

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
| 8. API Surface & Deployment | v1.1 | 0/? | Not started | - |
