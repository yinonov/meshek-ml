---
phase: 12-wire-contract
plan: 01
subsystem: api
tags: [pydantic, schema, tier-constructors, wire-contract, lightgbm]

# Dependency graph
requires:
  - phase: phase-6
    provides: ProductRecommendation, RecommendationResponse, tier constructors

provides:
  - Signal Pydantic model (name/contribution/copy_key) in recommendation/schema.py
  - ProductRecommendation with predicted_demand/demand_lower/demand_upper/reasoning_tier/confidence_score/signals per WIRE-01..WIRE-04
  - RecommendationResponse without response-level reasoning_tier/confidence_score per WIRE-02/WIRE-03
  - Three tier constructors emitting new v1.2 shape with per-line signals
  - SERVICE_VERSION bumped to 1.2.0
  - All 5 unit test files migrated inline to per-line assertions

affects: [phase-12-wire-contract, phase-14, meshek-app-typescript-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "model_validator(mode='after') for cross-field band invariant enforcement in Pydantic v2"
    - "Field(min_length=1) on list[Signal] to enforce at least one signal per recommendation line"
    - "Confidence computed before per-product loop to avoid NameError in tier constructors (Pitfall 8)"

key-files:
  created: []
  modified:
    - src/meshek_ml/recommendation/schema.py
    - src/meshek_ml/recommendation/tiers.py
    - src/meshek_ml/service/schemas.py
    - tests/recommendation/test_schema.py
    - tests/recommendation/test_tier_1.py
    - tests/recommendation/test_tier_2.py
    - tests/recommendation/test_tier_3.py
    - tests/recommendation/test_engine.py
    - tests/recommendation/test_engine_integration.py

key-decisions:
  - "Signal stays import-local to tiers.py and schema tests; NOT added to recommendation/__init__.py re-exports (no external consumer in Phase 12)"
  - "Tier 2 rounding bumped from round(q,2) to round(q,4) per WIRE-01 precision requirement; test_shrinkage_weights updated to round(40/3,4)"
  - "optimal_order_normal removed from tiers.py import and Tier 3 response path; mu exposed directly as predicted_demand (WIRE-05)"
  - "underage_cost/overage_cost parameters kept in tier_3_ml_forecast signature for backward compatibility even though unused"

patterns-established:
  - "Per-line reasoning_tier/confidence_score on ProductRecommendation, not response envelope"
  - "signals: list[Signal] = Field(min_length=1) — at least one tier-name signal per recommendation line"
  - "Demand band placeholder pattern: demand_lower=demand_upper=predicted_demand for Tier 1/2; Phase 14 fills variance"

requirements-completed: [WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05, WIRE-06]

# Metrics
duration: 25min
completed: 2026-05-04
---

# Phase 12 Plan 01: Schema and Tiers Summary

**v1.2 wire contract live: Signal+ProductRecommendation rewrites drop `quantity`, add per-line demand band and signals; all three tier constructors and 5 test files migrated inline**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-04
- **Completed:** 2026-05-04
- **Tasks:** 2 (both TDD)
- **Files modified:** 9

## Accomplishments

- New `Signal` Pydantic model and rewritten `ProductRecommendation` with band validator (`demand_lower <= predicted_demand <= demand_upper`) and `signals: list[Signal] = Field(min_length=1)`
- `RecommendationResponse` slimmed: response-level `reasoning_tier` and `confidence_score` removed (now per-line on each recommendation)
- All three tier constructors emit new shape with one tier-name signal each; `optimal_order_normal` fully removed from `tiers.py`
- `SERVICE_VERSION` bumped to `"1.2.0"` marking the breaking wire change
- 9 test files migrated inline (5 planned + `test_engine_integration.py` deviation fix); 51 tests pass

## Task Commits

1. **Task 1: Rewrite recommendation/schema.py + test_schema.py** - `1c9b117` (feat)
2. **Task 2: Rewrite tiers.py, bump SERVICE_VERSION, migrate tier/engine tests** - `7b905b6` (feat)

## Files Created/Modified

| File | Lines changed | Description |
|------|--------------|-------------|
| `src/meshek_ml/recommendation/schema.py` | +62 / -10 | Add Signal; rewrite ProductRecommendation (new fields + band validator); slim RecommendationResponse |
| `src/meshek_ml/recommendation/tiers.py` | +55 / -29 | Remove newsvendor import/call; add Signal import; rewrite all three tier constructors |
| `src/meshek_ml/service/schemas.py` | +1 / -1 | Bump SERVICE_VERSION "1.1.0" → "1.2.0" |
| `tests/recommendation/test_schema.py` | +72 / -28 | Full rewrite: _valid_product_rec_kwargs helper, 4 migrated test functions |
| `tests/recommendation/test_tier_1.py` | +7 / -4 | Per-line assertions; add signals assertions |
| `tests/recommendation/test_tier_2.py` | +8 / -8 | Per-line assertions; round(40/3,4) precision update |
| `tests/recommendation/test_tier_3.py` | +3 / -3 | Per-line assertions; rename test_quantities_non_negative → test_predicted_demand_non_negative |
| `tests/recommendation/test_engine.py` | +14 / -14 | 7 assertion locations migrated to .recommendations[0] |
| `tests/recommendation/test_engine_integration.py` | +8 / -8 | Deviation fix: per-line assertions (see below) |

## Test Migration Delta

| File | Assertions changed | Type |
|------|--------------------|------|
| test_schema.py | All 4 test functions fully rewritten | helper + test rewrite |
| test_tier_1.py | 2 per-line + 2 new signals assertions | field rename + addition |
| test_tier_2.py | 5 assertion locations | field rename + precision |
| test_tier_3.py | 4 assertion locations + test rename | field rename + rename |
| test_engine.py | 7 assertion locations (14 lines) | field rename |
| test_engine_integration.py | 6 assertion locations (deviation) | field rename |

## Decisions Made

- `Signal` NOT added to `recommendation/__init__.py` — no external consumer confirmed by grep; stays import-local to `tiers.py` and schema tests. Phase 14 may expose when Literal enum locks.
- Rounding precision bumped from `round(q, 2)` to `round(q, 4)` in Tier 2 per WIRE-01 precision requirement. Test expectation updated to `round(40/3, 4)`.
- `underage_cost`/`overage_cost` kept in `tier_3_ml_forecast` signature for backward compatibility. Unused inside function body — ruff ARG001 not in project config so no lint issue.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_engine_integration.py had response-level assertions not listed in plan**
- **Found during:** Task 2 (tier/engine test migration)
- **Issue:** `tests/recommendation/test_engine_integration.py` contained 6 response-level `r1.reasoning_tier`, `r1.confidence_score`, etc. assertions that broke after schema change. This file was not in the plan's `files_modified` list.
- **Fix:** Migrated all 6 assertion locations inline to `r1.recommendations[0].reasoning_tier` etc. — same per-line pattern applied consistently.
- **Files modified:** `tests/recommendation/test_engine_integration.py`
- **Verification:** `pytest tests/recommendation/ -x` passes (51/51)
- **Committed in:** `7b905b6` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: missing file in plan scope)
**Impact on plan:** Necessary for test suite correctness. No scope creep — same migration pattern applied consistently.

## Issues Encountered

- Ruff flagged `UP037` (quoted forward ref), `E501` (line length), `RUF002` (ambiguous sigma char), and `B905` (zip without strict) in new tiers.py and schema.py. All fixed inline before Task 2 commit.
- `service/schemas.py` and `engine.py`/`cli_train.py` have pre-existing ruff warnings (UP037, UP035, I001) that are out of scope for this plan.

## Newsvendor Decoupling Confirmation

`optimal_order_normal` is no longer imported or called from `tiers.py`. Verification:
- `grep -c 'optimal_order_normal' src/meshek_ml/recommendation/tiers.py` → 0
- The function remains in `src/meshek_ml/optimization/newsvendor.py` as an internal utility.

## pytest Output Summary

```
51 passed in 6.31s
```

All tests in `tests/recommendation/` pass including:
- 4 schema tests (new shape validation)
- 4 tier_1 tests
- 6 tier_2 tests
- 5 tier_3 tests (integration)
- 8 engine tests
- 1 engine integration test (integration)
- 16 other recommendation tests (model bundle, pooled store, etc.)

## Ruff Status

- `src/meshek_ml/recommendation/schema.py` — All checks passed
- `src/meshek_ml/recommendation/tiers.py` — All checks passed
- `src/meshek_ml/service/schemas.py` — Pre-existing UP037 (out of scope)

## Next Phase Readiness

- Schema v1.2 contract frozen: `Signal`, `ProductRecommendation` (new fields), `RecommendationResponse` (no response-level tier/score)
- Ready for plan 12-02: service-layer test migration (`tests/service/test_recommend.py` OpenAPI + contract tests)
- Ready for plan 12-03: WIRE-07 TypeScript client coordinated PR
- Phase 14 can fill demand band variance and tighten `Signal.name` to Literal once ready

---
*Phase: 12-wire-contract*
*Completed: 2026-05-04*
