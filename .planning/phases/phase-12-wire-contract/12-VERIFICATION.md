---
phase: 12
verified: 2026-05-04T00:00:00Z
status: passed
must_haves_verified: 14/14
human_verification_count: 0
overrides_applied: 0
---

# Phase 12: wire-contract Verification Report

**Phase Goal:** Land the new `/recommend` response contract — point estimate, demand band, per-line `reasoning_tier`, per-line `confidence_score`, and `signals[]` — and remove the order-quantity field. Cross-repo synchronization point with meshek v0.8.
**Verified:** 2026-05-04
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ProductRecommendation` has `predicted_demand`, `demand_lower`, `demand_upper`, `reasoning_tier`, `confidence_score`, `signals` and NO `quantity` field | VERIFIED | `schema.py` lines 41-48 declare all five new fields; `grep 'quantity' schema.py` returns only the module docstring line, zero field declarations |
| 2 | `Signal` model has `name` (str), `contribution` (float), `copy_key` (str) | VERIFIED | `schema.py` lines 18-31 — all three fields declared on `Signal(BaseModel)` |
| 3 | `RecommendationResponse` has `merchant_id`, `recommendations`, `generated_at` and NO response-level `reasoning_tier` or `confidence_score` | VERIFIED | `schema.py` lines 60-70 — field body contains exactly three fields; docstring mentions removed fields but no code declarations |
| 4 | All three tier constructors emit the new `ProductRecommendation` shape with exactly one tier-name `Signal` per line | VERIFIED | `tiers.py` — `signals=\[Signal(` count = 3 (one per tier); `predicted_demand=` count = 3; all constructors confirmed in source read |
| 5 | `tier_3_ml_forecast` does NOT call `optimal_order_normal` anywhere | VERIFIED | `grep -c 'optimal_order_normal' tiers.py` → 0 |
| 6 | `tiers.py` imports `Signal` and does NOT import `optimal_order_normal` | VERIFIED | `tiers.py` lines 25-29: `from meshek_ml.recommendation.schema import ProductRecommendation, RecommendationResponse, Signal`; no newsvendor import line |
| 7 | `SERVICE_VERSION` in `service/schemas.py` is `"1.2.0"` | VERIFIED | `schemas.py` line 24: `SERVICE_VERSION = "1.2.0"`; `grep '"1.1.0"' schemas.py` → 0 |
| 8 | Unit tests in `tests/recommendation/` pass with no `quantity` references and per-line assertions | VERIFIED | `pytest tests/recommendation/ -x` — 51/51 passed (embedded in 219 total); `grep '\.quantity' test_tier_*.py` → 0 |
| 9 | `POST /recommend` returns body with per-line `reasoning_tier` and `confidence_score` (no response-level fields) | VERIFIED | `test_recommend_tier1/2/3` and `test_tier1_in_degraded_mode` all assert `body["recommendations"][0]["reasoning_tier"]`; no top-level access remains |
| 10 | `GET /openapi.json` exposes `ProductRecommendation.properties` with all new fields and NO `quantity` | VERIFIED | `test_openapi_wire_contract` PASSED — checks `predicted_demand`, `demand_lower`, `demand_upper`, `reasoning_tier`, `confidence_score`, `signals` present; `quantity` absent |
| 11 | `GET /openapi.json` exposes `RecommendationResponse.properties` WITHOUT `reasoning_tier` or `confidence_score` | VERIFIED | `test_openapi_wire_contract` PASSED — asserts both are absent from `rr_props` |
| 12 | `tests/service/test_recommend.py` contains `test_openapi_wire_contract` and `test_tier1_contract_key_set` | VERIFIED | Both functions confirmed in source read at lines 161 and 177; both PASSED in `-v` test run |
| 13 | Full pytest suite passes (219+ tests) | VERIFIED | `pytest tests/ -x --tb=short` → 219 passed, 2 skipped, 3 warnings in 19.92s |
| 14 | Cross-repo handoff document exists with TypeScript diffs, merge sequence, and PR URL placeholders (WIRE-07) | VERIFIED (manual gate accepted per objective) | `12-03-CROSS-REPO-HANDOFF.md` exists; `predicted_demand: number` present; 2 `<URL — fill in when opened>` placeholders; `Merge the meshek PR FIRST` present; no `gh pr create/git push/git clone` in file |

**Score:** 14/14 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/meshek_ml/recommendation/schema.py` | `Signal`, new `ProductRecommendation`, slim `RecommendationResponse` | VERIFIED | 71 lines; `class Signal` at line 18, band validator at line 50, no response-level fields |
| `src/meshek_ml/recommendation/tiers.py` | All three tier constructors emitting new shape; `Signal` imported; newsvendor removed | VERIFIED | 181 lines; `Signal` in import block; 3x `signals=[Signal(...)]; 0x `optimal_order_normal` |
| `src/meshek_ml/service/schemas.py` | `SERVICE_VERSION = "1.2.0"` | VERIFIED | Line 24 confirms literal `"1.2.0"` |
| `tests/recommendation/test_schema.py` | Rewritten with `_valid_product_rec_kwargs` helper, 4 test functions | VERIFIED | Helper at line 16; 4 test functions at lines 45, 53, 63, 74; all 4 PASSED |
| `tests/service/test_recommend.py` | Per-line HTTP assertions + `test_openapi_wire_contract` + `test_tier1_contract_key_set` | VERIFIED | 210 lines; both new test functions present and PASSED |
| `.planning/phases/phase-12-wire-contract/12-03-CROSS-REPO-HANDOFF.md` | Cross-repo instruction set with TS diffs, merge sequence, URL placeholders | VERIFIED | All acceptance criteria pass (see truth 14) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tier_1/2/3` constructors | `ProductRecommendation(...)` | `predicted_demand=` + `signals=[Signal(...)]` | WIRED | 3 occurrences confirmed in `tiers.py` |
| `tier_3_ml_forecast` | (no longer) `optimal_order_normal` | newsvendor call removed; `mu` used directly | VERIFIED ABSENT | `grep -c 'optimal_order_normal' tiers.py` → 0 |
| `test_openapi_wire_contract` | `GET /openapi.json` | `app_client.get('/openapi.json')` → `schema['components']['schemas']['ProductRecommendation']['properties']` | WIRED | Test exists at line 161; PASSED |
| `test_tier1_contract_key_set` | `POST /recommend` (Tier 1) | `_seed_merchant + app_client.post` | WIRED | Test exists at line 177; PASSED |
| `RecommendationResponse` (no response-level fields) | OpenAPI JSON output | FastAPI auto-generates from Pydantic model | WIRED | `test_openapi_wire_contract` confirms `reasoning_tier` and `confidence_score` absent from `rr_props` |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `tiers.py::tier_1_category_defaults` | `predicted_demand` | `p.default_quantity` from `CategoryDefaultsConfig` | Yes — reads YAML config | FLOWING |
| `tiers.py::tier_2_pooled_priors` | `predicted_demand` | `shrink * own_mean + (1-shrink) * pooled_mean` from `PooledStore` | Yes — real shrinkage calculation | FLOWING |
| `tiers.py::tier_3_ml_forecast` | `predicted_demand` | `float(mean_demand)` from `model.predict(x)` (LightGBM) | Yes — real model inference | FLOWING |
| `tiers.py::tier_3_ml_forecast` | `demand_lower/upper` | `mu_f ± float(residual_std)` | Yes — derived from model residual | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `test_openapi_wire_contract` passes | `pytest tests/service/test_recommend.py::test_openapi_wire_contract -v` | PASSED | PASS |
| `test_tier1_contract_key_set` passes | `pytest tests/service/test_recommend.py::test_tier1_contract_key_set -v` | PASSED | PASS |
| Full suite 219+ | `pytest tests/ -x --tb=short` | 219 passed, 2 skipped | PASS |
| No `quantity=` constructor calls remain | `grep -rn 'ProductRecommendation(.*quantity=' tests/ src/` | 0 lines | PASS |
| `optimal_order_normal` absent from tiers.py | `grep -c 'optimal_order_normal' src/meshek_ml/recommendation/tiers.py` | 0 | PASS |
| `SERVICE_VERSION == "1.2.0"` | `grep '"1.2.0"' src/meshek_ml/service/schemas.py` | 1 match | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WIRE-01 | 12-01 | `ProductRecommendation` has `predicted_demand`, `demand_lower`, `demand_upper`; band validator enforced; `quantity` removed | SATISFIED | `schema.py` field declarations + `model_validator`; tests confirm `quantity` absent from `model_dump()` |
| WIRE-02 | 12-01 | `reasoning_tier` moved to per-line (removed from response level) | SATISFIED | `RecommendationResponse` body has no `reasoning_tier` field; all tier tests assert `recommendations[0].reasoning_tier` |
| WIRE-03 | 12-01 | `confidence_score` moved to per-line (removed from response level) | SATISFIED | Same evidence as WIRE-02; `test_tier1_contract_key_set` asserts `"confidence_score" not in body` |
| WIRE-04 | 12-01 | `signals: list[Signal]` with at least 1 entry per line; `Signal` has `name`, `contribution`, `copy_key` | SATISFIED | `Field(min_length=1)` enforced; all three tiers emit 1 Signal; `test_product_recommendation_fields` asserts empty signals raises |
| WIRE-05 | 12-01 | Newsvendor (`optimal_order_normal`) removed from Tier 3 response path; `mu` used directly as `predicted_demand` | SATISFIED | 0 occurrences of `optimal_order_normal` in `tiers.py`; Tier 3 uses `float(mean_demand)` directly |
| WIRE-06 | 12-02 | OpenAPI schema reflects new wire shape; `quantity` absent; new per-line fields present | SATISFIED | `test_openapi_wire_contract` PASSED; `ProductRecommendation` properties verified in live OpenAPI JSON |
| WIRE-07 | 12-03 | Cross-repo handoff document delivered with TypeScript diffs and merge sequence | SATISFIED (manual gate) | `12-03-CROSS-REPO-HANDOFF.md` exists with all required sections; meshek-side execution queued as P50 first plan per 12-03-SUMMARY.md |

---

## Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `src/meshek_ml/service/schemas.py` | UP037 quoted forward ref on line 97 | Info (pre-existing) | Out of scope for Phase 12; documented in 12-01-SUMMARY.md as pre-existing |
| `src/meshek_ml/recommendation/engine.py` | UP035 `typing.Callable` | Info (pre-existing) | Pre-existing; not introduced by Phase 12 |
| Various `src/meshek_ml/service/` files | I001/UP035/N806/E501 | Info (pre-existing) | Pre-existing; ruff passes clean on Phase 12 files (`schema.py`, `tiers.py`) |

No blockers. The ruff issues are all pre-existing and not in Phase 12 files. `ruff check src/meshek_ml/recommendation/schema.py src/meshek_ml/recommendation/tiers.py` passes with "All checks passed!"

---

## Human Verification Required

None. All verifiable behaviors confirmed programmatically.

WIRE-07 cross-repo coordination is a manual gate by design (CONTEXT.md locked decision; plan 12-03 is `autonomous: false`). The meshek-ml side has shipped the handoff doc and the meshek-side execution is queued via P50 first plan. Per verification objective: this is not counted as a code-side gap.

---

## Gaps Summary

No gaps. All 14 must-haves verified. The phase goal is achieved: the new `/recommend` response contract is live in the codebase with `predicted_demand`, `demand_lower`, `demand_upper`, per-line `reasoning_tier`, per-line `confidence_score`, and `signals[]`; `quantity` is removed; newsvendor is decoupled from the response path; `SERVICE_VERSION` is `"1.2.0"`; OpenAPI reflects the new shape; and the cross-repo handoff document is ready.

---

_Verified: 2026-05-04_
_Verifier: Claude (gsd-verifier)_

## VERIFICATION COMPLETE
