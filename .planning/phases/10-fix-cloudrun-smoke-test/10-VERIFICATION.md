---
phase: 10-fix-cloudrun-smoke-test
verified: 2026-04-16T00:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run smoke test against live Cloud Run service"
    expected: "All three steps (POST /merchants, POST /sales, POST /recommend) return expected status codes and response fields; test exits 0"
    why_human: "Requires MESHEK_CLOUDRUN_SMOKE=1 and MESHEK_CLOUDRUN_URL env vars pointing at the live Cloud Run URL; cannot run without live service access"
---

# Phase 10: Fix Cloud Run Smoke Test Verification Report

**Phase Goal:** The automated Cloud Run smoke test (`test_cloudrun_smoke.py`) calls the correct API paths and asserts the correct response fields, so the "Automated Cloud Run smoke" E2E flow passes without manual verification
**Verified:** 2026-04-16
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `test_cloudrun_smoke.py` calls `POST /sales` with `merchant_id` in the request body (not `/merchants/{id}/sales`) | VERIFIED | `_post("/sales", {"merchant_id": merchant_id, "date": ..., "text": ...})` confirmed at lines 77-84; no `/merchants/{merchant_id}/sales` references remain (0 grep hits) |
| 2 | `test_cloudrun_smoke.py` calls `POST /recommend` with `merchant_id` in the request body (not `/merchants/{id}/recommend`) | VERIFIED | `_post("/recommend", {"merchant_id": merchant_id})` confirmed at line 96; no `/merchants/{merchant_id}/recommend` references remain |
| 3 | Response assertions check for `accepted_rows` and `skipped` fields (not `parsed`) | VERIFIED | Lines 86-93 assert `"accepted_rows" in body`, `isinstance(body["accepted_rows"], int) and body["accepted_rows"] >= 1`, `"skipped" in body`, `isinstance(body["skipped"], list)`; `"parsed" in body` — 0 occurrences |
| 4 | Smoke test passes syntax validation (pytest collection succeeds without env vars) | VERIFIED | `python -c "import ast; ast.parse(...)"` exits 0; syntax confirmed valid |
| 5 | The smoke test passes when run against the live Cloud Run service with `MESHEK_CLOUDRUN_SMOKE=1` | UNCERTAIN | Requires live Cloud Run URL — see Human Verification Required |

**Score:** 4/5 truths verified (SC-4 needs live service)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/deploy/test_cloudrun_smoke.py` | Corrected Cloud Run smoke test aligned with Phase 8 API contract | VERIFIED | File exists, substantive (104 lines), committed in c045ed7; contains `"/sales"`, `"/recommend"`, `accepted_rows`, `skipped` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/deploy/test_cloudrun_smoke.py` | `src/meshek_ml/service/routes/sales.py` | POST /sales flat path with merchant_id in body | WIRED | Test calls `_post("/sales", {...})` with `merchant_id` and `date`; route decorator is `@router.post("/sales")`; `SalesResponse` schema has `accepted_rows: int` and `skipped: list[SkippedLine]` — exact match |
| `tests/deploy/test_cloudrun_smoke.py` | `src/meshek_ml/service/routes/recommend.py` | POST /recommend flat path with merchant_id in body | WIRED | Test calls `_post("/recommend", {"merchant_id": merchant_id})`; route decorator is `@router.post("/recommend")`; `RecommendRequest` schema has `merchant_id: MerchantIdStr` — exact match |

### Data-Flow Trace (Level 4)

Not applicable — `test_cloudrun_smoke.py` is a test client, not a component that renders dynamic data from a local state/store. Data flows through live HTTP calls to Cloud Run; verified at the schema/contract level above.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python syntax valid | `python -c "import ast; ast.parse(open('tests/deploy/test_cloudrun_smoke.py').read())"` | exits 0 | PASS |
| No old path-per-merchant references | grep for `/merchants/{merchant_id}/sales` and `/merchants/{merchant_id}/recommend` | 0 matches each | PASS |
| Flat `/sales` path present | regex scan of `_post(...)` calls | `_post("\n        \"/sales\"` confirmed | PASS |
| Flat `/recommend` path present | regex scan of `_post(...)` calls | `_post("/recommend", ...)` confirmed | PASS |
| `accepted_rows` assertion present | string search | 3 occurrences | PASS |
| `skipped` assertion present | string search | present | PASS |
| `from datetime import date as _date` present | string search | present at line 32 | PASS |
| Live Cloud Run E2E pass | `MESHEK_CLOUDRUN_SMOKE=1 MESHEK_CLOUDRUN_URL=<url> pytest tests/deploy/test_cloudrun_smoke.py -x -v` | not run | SKIP — needs live service |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-03 | 10-01-PLAN.md | Service runs on Google Cloud Run with per-merchant SQLite files persisted via GCS FUSE volume mount; smoke test verifies this E2E | PARTIAL | Test file contract is fully correct (paths, payloads, assertions all verified against actual API). Full satisfaction requires live Cloud Run run with `MESHEK_CLOUDRUN_SMOKE=1`. REQUIREMENTS.md traceability row: Phase 8.1, 10 — Pending. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No TODOs, stubs, hardcoded empty arrays, or placeholder returns found in `tests/deploy/test_cloudrun_smoke.py` |

### Human Verification Required

#### 1. Live Cloud Run Smoke Test

**Test:** With the `meshek-ml` service deployed and running on Cloud Run (`meshek-prod` project, `me-west1` region), run:

```
MESHEK_CLOUDRUN_SMOKE=1 \
MESHEK_CLOUDRUN_URL="$(gcloud run services describe meshek-ml --region me-west1 --format='value(status.url)')" \
uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v
```

**Expected:** All three steps pass:
- `POST /merchants {}` returns 201 with a `merchant_id` string
- `POST /sales {merchant_id, date, text}` returns 200 with `accepted_rows >= 1` and `skipped` list
- `POST /recommend {merchant_id}` returns 200 with a `recommendations` list

Test exits 0.

**Why human:** Requires `MESHEK_CLOUDRUN_URL` env var pointing to the live Cloud Run service. The service URL is not embedded in any committed file. Cannot run without live GCP access and a deployed service.

### Gaps Summary

No automated gaps. The test file is fully correct: paths, payloads, imports, assertions, and docstring all match the Phase 8 API contract exactly, as confirmed by:

1. Direct file inspection showing the correct `_post("/sales", ...)` and `_post("/recommend", ...)` calls
2. Schema alignment — `SalesResponse` has `accepted_rows: int` and `skipped: list[SkippedLine]`; `RecommendRequest` has `merchant_id: MerchantIdStr`
3. Zero residual references to the old path-per-merchant routes
4. Syntax validity confirmed

The only remaining item before INFRA-03 is fully closed is a live Cloud Run run with the env guard disabled (human verification item 1 above). This is by design — the test has a `_SMOKE_ENABLED` guard that skips it in normal CI, which is correct behavior.

---

_Verified: 2026-04-16_
_Verifier: Claude (gsd-verifier)_
