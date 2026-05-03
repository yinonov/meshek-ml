---
phase: 06-recommendation-engine
verified: 2026-04-14T00:00:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 6: Recommendation Engine Verification Report

**Phase Goal:** The service can produce a confidence-scored order recommendation for any merchant regardless of how much history they have.

**Verified:** 2026-04-14
**Status:** passed
**Re-verification:** No — initial verification
**Test run:** `.venv/bin/python -m pytest tests/recommendation tests/service -q --no-cov` → **51 passed in 6.88s**

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A merchant with zero sales history receives a Tier-1 category-default recommendation | VERIFIED | `engine.py:67-68` branches on `sales.empty` first (Pitfall 4 guard) then on `n_days == 0`, calling `tier_1_category_defaults` which returns `reasoning_tier="category_default"`, `confidence_score=0.2` (`tiers.py:32-51`). Test: `test_engine.py::test_tier_1_routing_zero_days` (PASS) asserts tier + score on a factory merchant with `days=0`. |
| 2 | A merchant with <14 days of history receives a Tier-2 pooled-prior recommendation | VERIFIED | `engine.py:72-78` routes `1 <= n_days < 14` to `tier_2_pooled_priors`, which blends own means with `PooledStore.pooled_mean_by_product(exclude_merchant_id=...)` using shrinkage `n/(n+14)` and returns `reasoning_tier="pooled_prior"` with linearly interpolated confidence in `[0.3, 0.6]` (`tiers.py:54-87`). Tests: `test_tier_2_routing_at_1_day`, `test_tier_2_routing_at_13_days`, `test_confidence_bounds_per_tier` (all PASS). |
| 3 | A merchant with 14+ days of history receives a LightGBM-forecasted Tier-3 recommendation | VERIFIED | `engine.py:79-90` routes `n_days >= 14` to `tier_3_ml_forecast` (`tiers.py:90-159`), which reuses `forecasting.features.*` (lag/rolling/calendar), imputes NaN warmup rows, calls `model.predict`, and converts mean demand to order qty via `optimal_order_normal` newsvendor. Returns `reasoning_tier="ml_forecast"` with confidence clipped to `[0.6, 0.95]`. Tests: `test_tier_3_routing_at_14_days` and `test_tier_3_routing_at_30_days` (both integration, PASS) assert the boundary and interior. |
| 4 | Every recommendation response includes `reasoning_tier` and `confidence_score` fields | VERIFIED | `schema.py:14` locks `ReasoningTier = Literal["category_default", "pooled_prior", "ml_forecast"]`. `RecommendationResponse` (`schema.py:25-32`) requires `reasoning_tier: ReasoningTier` and `confidence_score: float = Field(ge=0.0, le=1.0)`. All three tier builders populate both fields. Tests: `test_response_contract_rec04`, `test_schema.py` (4 cases) — PASS. |
| 5 | LightGBM model loads once at startup via FastAPI lifespan, not per-request | VERIFIED | `service/lifespan.py:44-75` defines `build_lifespan(model_path)` as an `@asynccontextmanager`, resolves `MESHEK_MODEL_PATH` → default, fails fast on missing file, calls `load_model_bundle` once, and attaches an `AppState` to `app.state.ml` (never a module global). Teardown clears state. Tests (all PASS): `test_loads_on_startup`, `test_missing_model_file`, `test_env_var_fallback`, `test_default_path_when_no_env`, `test_loader_called_once` (monkeypatches loader and asserts `counter == 1` after 5 `GET /ping` calls), `test_teardown_clears_state`. Additional guard: `test_tier_3.py::test_inference_never_reads_disk` monkeypatches `load_model_bundle` to raise and runs Tier-3 inference 5× successfully. |

**Score:** 5/5 truths verified

### Required Artifacts (Level 1–3)

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `src/meshek_ml/recommendation/schema.py` | Pydantic response contract with locked tier Literal + bounded confidence | VERIFIED | 33 lines, exports `ReasoningTier`, `ProductRecommendation`, `RecommendationResponse`. Imported by `tiers.py`, `engine.py`, and tests. |
| `src/meshek_ml/recommendation/tiers.py` | Three tier functions producing `RecommendationResponse` | VERIFIED | 159 lines, implements T1/T2/T3 with correct confidence ranges. Used by `engine.py`. |
| `src/meshek_ml/recommendation/engine.py` | `RecommendationEngine.recommend()` routing on `sales["date"].nunique()` | VERIFIED | 90 lines, empty-guard + threshold router, injects pre-loaded model. |
| `src/meshek_ml/recommendation/pooled_store.py` | Cross-merchant mean lookup with own-merchant exclusion | VERIFIED | Exercised by `test_pooled_store.py` (5 tests PASS) and by Tier-2 runtime path. |
| `src/meshek_ml/recommendation/config.py` | `CategoryDefaultsConfig` loader | VERIFIED | `test_config.py` (2 tests PASS). Consumed by Tier 1. |
| `src/meshek_ml/recommendation/model_io.py` | `save_model_bundle` / `load_model_bundle` with traversal guard + key validation | VERIFIED | 82 lines, `_assert_within_root` enforces `relative_to(MESHEK_MODELS_DIR)`, required keys checked. `test_model_io.py` (5 tests PASS). |
| `src/meshek_ml/recommendation/training.py` | `train_and_save()` producing a bundle | VERIFIED | `test_training.py` (5 tests PASS). Produces the fixture used by lifespan + Tier-3 tests. |
| `src/meshek_ml/service/lifespan.py` | `build_lifespan` factory attaching `AppState` to `app.state.ml` | VERIFIED | 76 lines; lifespan tests cover happy, missing-file, env fallback, default, loader-called-once, teardown. |
| `src/meshek_ml/service/state.py` | `AppState` dataclass | VERIFIED | 19 lines; frozen field layout consumed by lifespan + Tier-3 injection. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `engine.recommend` | `tier_1/2/3` | Direct import + call on routed branch | WIRED | Verified by import + `test_engine.py` tier-routing tests. |
| `engine.__init__` | `MerchantStore` | `store_factory(merchant_id)` callable | WIRED | `_make_engine` in tests passes `lambda mid: MerchantStore(mid, must_exist=True)`; `UnknownMerchantError` test confirms failure mode. |
| `tier_2_pooled_priors` | `PooledStore.pooled_mean_by_product` | Direct call with `exclude_merchant_id` | WIRED | Integration test `test_engine_integration.py::test_three_tiers_single_run` (PASS). |
| `tier_3_ml_forecast` | `forecasting.features.*` + `optimization.newsvendor.optimal_order_normal` | Feature pipeline + newsvendor conversion | WIRED | Tier-3 integration tests PASS end-to-end with a trained bundle. |
| `build_lifespan` | `load_model_bundle` → `app.state.ml = AppState(...)` | Called once inside async context manager | WIRED | `test_loader_called_once` proves single call across 5 requests. |
| Request path | `app.state.ml` | Injected (not reloaded) | WIRED | `test_inference_never_reads_disk` monkeypatches loader to raise; 5 inference calls succeed. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `RecommendationResponse.recommendations` (T1) | `recs` | `CategoryDefaultsConfig.products` (YAML) | Yes (config-driven, 0-day merchant path) | FLOWING |
| `RecommendationResponse.recommendations` (T2) | `recs` | `PooledStore.pooled_mean_by_product` + own-sales groupby mean | Yes (requires ≥1 other merchant; fillers used in tests) | FLOWING |
| `RecommendationResponse.recommendations` (T3) | `recs` | Trained `LGBMRegressor.predict` on engineered lag/rolling/calendar features | Yes (live model in `trained_model_bundle` fixture) | FLOWING |
| `app.state.ml` | `bundle` | `joblib.load(MESHEK_MODEL_PATH)` via `load_model_bundle` | Yes (proven by `test_loads_on_startup`) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full Phase-6 test suite executes | `.venv/bin/python -m pytest tests/recommendation tests/service -q --no-cov` | 51 passed in 6.88s | PASS |
| Module import smoke | `python -c "from meshek_ml.recommendation import RecommendationEngine; from meshek_ml.service.lifespan import build_lifespan"` | (implicitly exercised by test collection; no ImportErrors) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| REC-01 | 06-02, 06-04 | Tier 1 category-default recommendations | SATISFIED | `tier_1_category_defaults` + `test_tier_1_routing_zero_days` |
| REC-02 | 06-02, 06-04 | Tier 2 pooled-prior recommendations | SATISFIED | `tier_2_pooled_priors` + `test_tier_2_*` + `PooledStore` tests |
| REC-03 | 06-03, 06-04 | Tier 3 LightGBM-forecasted recommendations | SATISFIED | `tier_3_ml_forecast` + `training.py` + Tier-3 routing tests |
| REC-04 | 06-01, 06-02, 06-04 | Response contract with `reasoning_tier` + `confidence_score` | SATISFIED | `schema.py` + `test_response_contract_rec04` + `test_schema.py` |
| INFRA-01 | 06-03, 06-04 | Model loaded once at startup | SATISFIED | `service/lifespan.py` + `test_loader_called_once` + `test_inference_never_reads_disk` |

All five declared requirements for this phase are marked Complete in `.planning/REQUIREMENTS.md`. No orphaned requirements.

### Anti-Patterns Found

None blocking. Observations:
- `tier_3_ml_forecast` confidence formula is a documented "placeholder" (`tiers.py:148`), bounded to `[0.6, 0.95]`; acceptable per plan scope.
- `engine.py:79-83` raises `RuntimeError` when Tier 3 is selected without an injected model — correct fail-loud behavior, not a stub.

### Human Verification Required

None. Every success criterion is covered by an automated test with concrete assertions (tier string, confidence band, load-count, disk-access guard). The FastAPI lifespan is exercised via `TestClient`, so no live server is required.

### Gaps Summary

No gaps. The phase goal is fully achieved: the engine produces a confidence-scored recommendation for any merchant depth (0, 1–13, 14+), the response contract is locked by Pydantic, and the LightGBM model is loaded exactly once at FastAPI startup and never from disk during inference. 51/51 Phase-6 tests pass.

---

_Verified: 2026-04-14_
_Verifier: Claude (gsd-verifier)_
