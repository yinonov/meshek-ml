---
phase: 12-wire-contract
plan: 02
subsystem: api
tags: [fastapi, openapi, contract-test, http-integration, wire-contract]

# Dependency graph
requires:
  - phase: 12-wire-contract
    plan: 01
    provides: Signal/ProductRecommendation/RecommendationResponse v1.2, three tier constructors, SERVICE_VERSION 1.2.0

provides:
  - tests/service/test_recommend.py with per-line HTTP assertions (WIRE-01..WIRE-04)
  - test_openapi_wire_contract: GET /openapi.json shape verified, quantity absent, new per-line fields present (WIRE-06)
  - test_tier1_contract_key_set: full key-set + types pinned for Tier 1 HTTP response (WIRE-01..WIRE-06)
  - Full pytest suite green (219 passed, 2 skipped)

affects: [phase-12-wire-contract, meshek-app-typescript-client]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTTP contract test via TestClient.get('/openapi.json') → schema['components']['schemas']['ProductRecommendation']['properties']"
    - "Superset assertion set(body.keys()) >= {...} pins required keys while allowing future additive fields"
    - "Explicit 'not in body' assertions for removed fields (reasoning_tier, confidence_score at response level)"

key-files:
  created: []
  modified:
    - tests/service/test_recommend.py
    - tests/service/test_health.py

key-decisions:
  - "Both new contract tests appended inline to tests/service/test_recommend.py (not a sibling file) — file is short enough (~210 lines total) that splitting adds no value"
  - "test_tier1_contract_key_set uses superset assertion (>=) for envelope keys per CONTEXT.md key_set decision: additive-safe, removes-pinned"

patterns-established:
  - "OpenAPI contract test pattern: GET /openapi.json → schema['components']['schemas'] key traversal"
  - "HTTP tier contract test pattern: _seed_merchant + app_client.post + per-line key-set + signals[0] key assertions"

requirements-completed: [WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-06]

# Metrics
duration: 2min
completed: 2026-05-05
---

# Phase 12 Plan 02: Service and OpenAPI Summary

**HTTP service tests migrated to per-line assertions; OpenAPI contract test and full Tier-1 key-set test appended; full pytest suite green (219 passed)**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-05
- **Completed:** 2026-05-05
- **Tasks:** 2
- **Files modified:** 2 (tests/service/test_recommend.py + tests/service/test_health.py deviation fix)

## Accomplishments

- 7 inline assertion migrations in `tests/service/test_recommend.py`: response-level `body["reasoning_tier"]` / `body["confidence_score"]` → `body["recommendations"][0]["reasoning_tier"]` etc.
- `test_openapi_wire_contract` appended: verifies GET /openapi.json exposes `predicted_demand`, `demand_lower`, `demand_upper`, `reasoning_tier`, `confidence_score`, `signals` on `ProductRecommendation`; confirms `quantity` absent; confirms `RecommendationResponse` has no response-level `reasoning_tier` or `confidence_score` (WIRE-06)
- `test_tier1_contract_key_set` appended: seeds a 0-day merchant, calls POST /recommend, pins envelope key superset, verifies per-line types (numeric demand/band, str tier/unit/product_id), signals[0] shape with `copy_key.startswith("signal.")` (WIRE-01..WIRE-06)
- Full wave-2 gate: 219 passed, 2 skipped in 11.92s

## Task Commits

1. **Task 1: Migrate service test assertions + append contract tests** — `eb667ba` (feat)
2. **Task 2: Wave-2 gate + deviation health test fix** — `13e123d` (fix)

## Files Created/Modified

| File | Lines changed | Description |
|------|--------------|-------------|
| `tests/service/test_recommend.py` | +63 / -7 | 7 per-line migrations + 2 new contract test functions |
| `tests/service/test_health.py` | +2 / -2 | Deviation fix: version "1.1.0" → "1.2.0" (Rule 1) |

## Service Test Migration Delta

| Test function | Lines changed | Type |
|---------------|--------------|------|
| `test_recommend_tier1` | 2 assertions | response-level → per-line |
| `test_recommend_tier2` | 2 assertions | response-level → per-line |
| `test_recommend_tier3` | 2 assertions | response-level → per-line |
| `test_tier1_in_degraded_mode` | 1 assertion | response-level → per-line |
| `test_openapi_wire_contract` (NEW) | 15 lines | OpenAPI schema contract (WIRE-06) |
| `test_tier1_contract_key_set` (NEW) | 33 lines | Full key-set + types pin (WIRE-01..WIRE-06) |

## New Contract Test Functions

### `test_openapi_wire_contract` — `tests/service/test_recommend.py:161`

Pins via `GET /openapi.json`:
- `ProductRecommendation.properties` includes: `predicted_demand`, `demand_lower`, `demand_upper`, `reasoning_tier`, `confidence_score`, `signals`
- `ProductRecommendation.properties` does NOT include: `quantity`
- `RecommendationResponse.properties` does NOT include: `reasoning_tier`, `confidence_score`

### `test_tier1_contract_key_set` — `tests/service/test_recommend.py:177`

Pins via `POST /recommend` (Tier 1, 0 days):
- Response envelope superset: `{"merchant_id", "recommendations", "generated_at"}`
- No response-level `reasoning_tier`, `confidence_score`, `quantity`
- Per-line: `product_id` (str), `unit` (str), `predicted_demand` / `demand_lower` / `demand_upper` (numeric), `reasoning_tier == "category_default"`, `0.0 <= confidence_score <= 1.0`, no `quantity`
- Signals: list with at least 1 entry; `name` (str), `contribution` (numeric), `copy_key.startswith("signal.")`

## Full pytest Suite Output Summary

```
219 passed, 2 skipped, 3 warnings in 11.92s
```

Skipped tests are infrastructure-dependent (Cloud Run smoke test, Docker smoke test) — correctly skipped via env-var guards.

## No quantity= Constructor Calls Remaining

`grep -rn 'ProductRecommendation(.*quantity=' tests/ src/ 2>/dev/null` → 0 lines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `tests/service/test_health.py` version assertion pinned to old "1.1.0"**
- **Found during:** Task 2 (full suite gate)
- **Issue:** `test_health_with_model` and `test_health_degraded` asserted `body["version"] == "1.1.0"`. Plan 01 bumped `SERVICE_VERSION` to `"1.2.0"`, making both tests fail. This file was not in Plan 02's `files_modified` list.
- **Fix:** Updated both assertions to `"1.2.0"` (2 lines, both occurrences in `test_health.py`).
- **Files modified:** `tests/service/test_health.py`
- **Commit:** `13e123d`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: version assertion stale after Plan 01 SERVICE_VERSION bump)

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. `GET /openapi.json` is an existing public FastAPI-generated endpoint — the test verifies its shape but does not change the endpoint behavior. T-12-04 (accepted) and T-12-05 (mitigated by new contract tests) per plan's threat register.

## Self-Check: PASSED

- `tests/service/test_recommend.py` exists: FOUND
- `tests/service/test_health.py` modified: FOUND
- Commit `eb667ba` exists: FOUND
- Commit `13e123d` exists: FOUND
- `grep -c '^def test_openapi_wire_contract' tests/service/test_recommend.py` → 1: PASS
- `grep -c '^def test_tier1_contract_key_set' tests/service/test_recommend.py` → 1: PASS
- Top-level body[reasoning_tier] accesses remaining → 0: PASS
- Full suite: 219 passed: PASS

## Next Phase Readiness

- Wire contract v1.2 fully verified end-to-end: Pydantic models → FastAPI → HTTP body → OpenAPI JSON
- Plan 12-03 unblocked: meshek-side TypeScript client can reference the stable, tested public shape
- `test_openapi_wire_contract` and `test_tier1_contract_key_set` serve as CI gate: any accidental schema regression will fail before shipping

---
*Phase: 12-wire-contract*
*Completed: 2026-05-05*
