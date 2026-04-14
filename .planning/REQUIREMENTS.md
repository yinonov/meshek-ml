# Requirements: meshek-ml

**Defined:** 2026-04-10
**Core Value:** Answer "how much should I order tomorrow?" for Israeli greengrocers — wrapping proven ML forecasting and optimization behind a zero-friction WhatsApp interface.

## v1.1 Requirements

Requirements for Merchant Order Advisor milestone. Each maps to roadmap phases.

### API Endpoints

- [ ] **API-01**: meshek app can check service health via `GET /health`
- [ ] **API-02**: meshek app can create a new merchant with zero configuration via `POST /merchants`
- [ ] **API-03**: meshek app can submit daily sales records for a merchant via `POST /sales`
- [ ] **API-04**: meshek app can get per-product order recommendations for a merchant via `POST /recommend`

### Recommendation Engine

- [x] **REC-01**: New merchant with no history receives recommendations based on product category defaults (Tier 1)
- [x] **REC-02**: Merchant with limited history receives recommendations using cross-merchant pooled priors (Tier 2)
- [x] **REC-03**: Merchant with 14+ days of sales history receives ML-forecasted recommendations via LightGBM pipeline (Tier 3)
- [x] **REC-04**: Every recommendation response includes `reasoning_tier` and `confidence_score`

### Hebrew Parsing

- [x] **PARSE-01**: Hebrew product names (singular/plural, common misspellings) are mapped to canonical product IDs
- [ ] **PARSE-02**: Quantity + unit extraction from Hebrew free text (e.g., "20 עגבניות" or "עגבניות 20")

### Storage

- [x] **STOR-01**: Sales history is persisted per-merchant in isolated SQLite files
- [x] **STOR-02**: Merchant profiles are created and retrievable

### Infrastructure

- [x] **INFRA-01**: LightGBM model loads once at startup via FastAPI lifespan (not per-request)
- [ ] **INFRA-02**: Service runs in a Docker container deployable to Railway/Fly.io

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Recommendation Engine

- **REC-05**: Async model retraining via `POST /retrain/{merchant_id}` with 202 Accepted
- **REC-06**: Israeli holiday calendar upgrade using `hdate` library for accurate Hebrew calendar dates
- **REC-07**: Per-product asymmetric cost parameters exposed in request (underage/overage costs)

### Hebrew Parsing

- **PARSE-03**: Fuzzy match fallback for misspelled Hebrew product names (rapidfuzz)

### Optimization

- **OPT-01**: PPO agent inference path as alternative to newsvendor
- **OPT-02**: Federated training across merchants for shared demand priors

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| WhatsApp integration | Owned by meshek app, not meshek-ml |
| Merchant dashboard/UI | Owned by meshek app, not meshek-ml |
| LLM-based Hebrew parsing | Dictionary-based is faster, cheaper, deterministic for ~30 products |
| Real-time streaming inference | Merchants order once/day at 2-3 AM; no value in real-time |
| Per-product models (one LightGBM per SKU) | Worse at low data volumes; M5 competition confirms |
| Dynamic pricing recommendations | Too personal/relational in Israeli culture; all 8 papers defer |
| Synchronous model retraining on /recommend | Blocks event loop; must be async or scheduled |
| Confidence intervals as primary output | Merchants need one number, not a range |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 8 | Pending |
| API-02 | Phase 8 | Pending |
| API-03 | Phase 8 | Pending |
| API-04 | Phase 8 | Pending |
| REC-01 | Phase 6 | Complete |
| REC-02 | Phase 6 | Complete |
| REC-03 | Phase 6 | Complete |
| REC-04 | Phase 6 | Complete |
| PARSE-01 | Phase 7 | Complete |
| PARSE-02 | Phase 7 | Pending |
| STOR-01 | Phase 5 | Complete |
| STOR-02 | Phase 5 | Complete |
| INFRA-01 | Phase 6 | Complete |
| INFRA-02 | Phase 8 | Pending |

**Coverage:**
- v1.1 requirements: 14 total
- Mapped to phases: 14
- Satisfied: 2 (STOR-01, STOR-02)
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after roadmap creation*
