---
phase: 08-api-surface-deployment
plan: "04"
subsystem: service
tags: [fastapi, recommend, recommendation-engine, lifespan, catalog-migration, tdd, wave-2]
dependency_graph:
  requires: [service/app.py, service/schemas.py, recommendation/engine.py, recommendation/schema.py, recommendation/config.py, recommendation/pooled_store.py, parsing/__init__.py]
  provides: [service/routes/recommend.py, POST /recommend endpoint, app.state.engine, app.state.catalog]
  affects: [plan 05 adds central error handler mapping RuntimeError -> 503 and UnknownMerchantError -> 404]
tech_stack:
  added: []
  patterns: [engine-cached-on-app-state, lifespan-composition, degraded-start-dual-path, catalog-on-app-state]
key_files:
  created:
    - src/meshek_ml/service/routes/recommend.py
  modified:
    - src/meshek_ml/service/schemas.py
    - src/meshek_ml/service/app.py
    - src/meshek_ml/service/routes/sales.py
    - tests/service/test_recommend.py
decisions:
  - "RecommendationEngine built once in lifespan for both happy (model loaded) and degraded (model=None) paths; both assign app.state.engine"
  - "Catalog loaded before phase6_lifespan try/except so it is available in both paths"
  - "No try/except in post_recommend handler — exceptions bubble to plan 05 central handler (D-11)"
  - "test_missing_model asserts status in (500, 503) with comment to tighten in plan 05"
  - "lru_cache _get_catalog() removed from routes/sales.py; reads request.app.state.catalog instead"
metrics:
  duration_min: 15
  tasks_completed: 2
  files_created: 1
  files_modified: 4
  completed_date: "2026-04-14"
requirements: [API-04, REC-04]
---

# Phase 8 Plan 04: POST /recommend + Engine Lifespan + Catalog Migration Summary

**One-liner:** `POST /recommend` wired to a singleton `RecommendationEngine` built at startup with degraded-start fallback; `app.state.catalog` replaces `lru_cache` in sales route so all routes share one loaded catalog.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-04-01 RED | Failing tests for all tiers + degraded mode | e9b9a12 | tests/service/test_recommend.py |
| 8-04-01 GREEN | Lifespan extension + /recommend handler + catalog migration | 35f6a8c | schemas.py, routes/recommend.py, app.py, routes/sales.py |
| 8-04-02 | Tier 3 no-model + Tier 1 degraded-mode tests (included in RED commit) | e9b9a12 | tests/service/test_recommend.py |

---

## What Was Built

### src/meshek_ml/service/schemas.py (extended)

- `RecommendRequest(merchant_id: MerchantIdStr)` — edge-validated request body (T-5-01)
- `RecommendationResponse` imported directly from `meshek_ml.recommendation.schema` and used as `response_model` (D-06/D-09 — reuse verbatim)

### src/meshek_ml/service/routes/recommend.py (new)

- `router = APIRouter()`
- `@router.post("/recommend", response_model=RecommendationResponse)`
- Sync `def post_recommend(body, request)` reads `request.app.state.engine`, calls `engine.recommend(body.merchant_id)`, returns the result directly
- No try/except — exceptions bubble to plan 05's central handler (D-11)

### src/meshek_ml/service/app.py (extended)

`_build_engine_lifespan` now:
- Loads parser catalog via `load_catalog(DEFAULT_CATALOG_PATH)` before entering the phase6 lifespan; assigns to `app.state.catalog`
- Loads `CategoryDefaultsConfig` from `configs/recommendation/category_defaults.yaml`
- Instantiates `PooledStore()`
- **Happy path** (inside `async with phase6_lifespan`): builds `RecommendationEngine` with `model`, `residual_std`, `feature_cols` from `app.state.ml`; assigns to `app.state.engine`
- **Degraded path** (on `RuntimeError` from model load): builds `RecommendationEngine` with `model=None, residual_std=0.0, feature_cols=[]`; Tier 1/2 still work; Tier 3 raises `RuntimeError` (plan 05 maps to 503)
- Teardown in both paths: clears `app.state.engine = None`, `app.state.catalog = None`
- `app.include_router(recommend.router)` added to `create_app()`

### src/meshek_ml/service/routes/sales.py (migrated)

- Removed `from functools import lru_cache` and `_get_catalog()` function
- Removed `DEFAULT_CATALOG_PATH` and `load_catalog` imports (no longer needed in this module)
- Free-text path now reads `catalog = request.app.state.catalog`
- Removed all TODO comments from plan 03

### tests/service/test_recommend.py (replaced stub)

Nine tests covering all required behaviors:

**Happy-path (app_client — model loaded):**
- `test_recommend_tier1` — zero sales → 200, `reasoning_tier == "category_default"`
- `test_recommend_tier2` — 3 days of sales (+ 2 filler merchants) → 200, `reasoning_tier == "pooled_prior"`, confidence in [0.3, 0.6]
- `test_recommend_tier3` — 20 days of sales → 200, `reasoning_tier == "ml_forecast"`, confidence in [0.6, 0.95]
- `test_engine_is_cached_on_app_state` — `app.state.engine is not None` after lifespan
- `test_catalog_on_app_state` — `app.state.catalog is not None` after lifespan
- `test_recommend_invalid_merchant_id` — path-traversal `merchant_id` → 422

**Degraded-mode (no_model_client — model file missing):**
- `test_missing_model` — 20 days of sales, no model → `status in (500, 503)` (plan 05 tightens to == 503)
- `test_tier1_in_degraded_mode` — zero sales, no model → 200, `reasoning_tier == "category_default"`

**Catalog migration verification:**
- `test_sales_uses_app_state_catalog` — Hebrew free-text POST /sales still works end-to-end after migration from `lru_cache` to `app.state.catalog`

---

## Verification Results

```
uv run pytest tests/service -x -q
29 passed, 1 skipped in 2.28s
```

- All 9 new recommend tests pass
- All prior health, lifespan, merchant, and sales tests still green
- Docker smoke placeholder still skipped (expected, plan 08-06)

---

## Deviations from Plan

**1. [Rule 2 - Implementation consolidation] Task 8-04-02 tests included in RED commit with 8-04-01**

- **Found during:** Task 8-04-01 TDD setup
- **Reason:** Plan 8-04-02 adds only two tests (`test_missing_model`, `test_tier1_in_degraded_mode`) with no source changes. Including them in the initial RED commit is cleaner than a separate test-only commit that would require temporarily incomplete assertions.
- **Impact:** Both tests passed GREEN immediately after the 8-04-01 implementation commit. No source-only commit needed for 8-04-02.
- **Files modified:** `tests/service/test_recommend.py`
- **Commit:** e9b9a12 (RED), 35f6a8c (GREEN for both tasks)

---

## Integration Notes

- Plan 05 adds the central exception handler mapping `UnknownMerchantError → 404` and `RuntimeError → 503`. Until then, `test_missing_model` accepts `status in (500, 503)` with a comment, and `test_sales_unknown_merchant` in test_sales.py accepts `status in (404, 500)`.
- The `_build_engine_lifespan` lifespan wrapper is now complete — plan 01 established the degraded-start contract, plans 02 and 03 added routes, plan 04 wired the engine and catalog. Plans 05+ add error handling and deployment.
- INFRA-01 upheld: `RecommendationEngine` is passed the model object from `app.state.ml` (loaded once in phase6_lifespan). No per-request `joblib.load()`.

---

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: input-validation | routes/recommend.py | `merchant_id` flows into `engine.recommend()` which calls `MerchantStore(mid, must_exist=True)` — `MerchantIdStr` regex on `RecommendRequest` ensures sanitization at edge (T-5-01 mitigated). |

No new trust boundaries beyond the plan's threat model.

---

## Known Stubs

None — all three tiers return real `RecommendationResponse` data from the Phase 6 engine. Degraded mode Tier 3 fails as designed.

---

## Self-Check: PASSED
