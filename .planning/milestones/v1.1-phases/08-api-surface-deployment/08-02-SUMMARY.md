---
phase: 08-api-surface-deployment
plan: "02"
subsystem: service
tags: [fastapi, merchants, path-traversal, pydantic-v2, tdd, wave-1]
dependency_graph:
  requires: [service/app.py, service/schemas.py, storage/merchant_store.py]
  provides: [service/routes/merchants.py, POST /merchants endpoint]
  affects: [plans 03-05 all share app.py and schemas.py]
tech_stack:
  added: []
  patterns: [Pydantic Annotated regex validation, uuid4.hex auto-id, MerchantStore context-manager per request]
key_files:
  created:
    - src/meshek_ml/service/routes/merchants.py
  modified:
    - src/meshek_ml/service/schemas.py
    - src/meshek_ml/service/app.py
    - tests/service/test_merchants.py
decisions:
  - "display_name in CreateMerchantRequest maps to MerchantProfile.name (storage model predates API naming)"
  - "MerchantIdStr reused from schemas.py as Annotated[str, Field(pattern=...)] — pydantic v2 idiom, not deprecated constr()"
  - "Response is raw MerchantProfile (D-06, D-12) — no envelope wrapper"
metrics:
  duration_min: 10
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  completed_date: "2026-04-15"
requirements: [API-02]
---

# Phase 8 Plan 02: POST /merchants Endpoint Summary

**One-liner:** `POST /merchants` with Pydantic-layer path-traversal guard (`MerchantIdStr` regex → 422 before FS I/O), uuid4.hex auto-id generation, and `MerchantStore.create_profile` persistence returning a raw `MerchantProfile`.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-02-01 RED | Failing tests for merchants endpoint | 94a6ebb | tests/service/test_merchants.py |
| 8-02-01 GREEN | schemas + handler + router wiring | 51b5c6e | schemas.py, routes/merchants.py, app.py |
| 8-02-02 | Auto-id test (test_auto_id) — GREEN via 8-02-01 implementation | 51b5c6e | tests/service/test_merchants.py |

---

## What Was Built

### src/meshek_ml/service/schemas.py (extended)
- `CreateMerchantRequest`: `merchant_id: MerchantIdStr | None = None`, `display_name: str | None = Field(default=None, max_length=128)`
- Reuses existing `MerchantIdStr` (plan 01) — no duplication of the regex
- `max_length=128` on `display_name` mitigates T-8-05 (oversized name DoS)

### src/meshek_ml/service/routes/merchants.py (new)
- `router = APIRouter()`
- `@router.post("/merchants", status_code=201, response_model=MerchantProfile)` — sync `def` (D-05)
- Auto-id: `uuid.uuid4().hex` when `body.merchant_id is None` (32 lowercase hex chars, D-07)
- `display_name` → `MerchantProfile.name` mapping (storage model field name)
- `with MerchantStore(merchant_id) as store: return store.create_profile(profile)` — context-manager per request

### src/meshek_ml/service/app.py (extended)
- `from meshek_ml.service.routes import health, merchants`
- `app.include_router(merchants.router)` alongside health router

### tests/service/test_merchants.py (replaced stub)
- `test_create_explicit_id`: 201 + `merchant_id == "shop_a"` round-trip
- `test_invalid_id_rejected_before_fs` (T-5-01): `../etc/passwd` → 422, asserts `merchants/*.sqlite` is empty
- `test_invalid_id_slash`: `a/b` → 422
- `test_invalid_id_too_long`: 65-char id → 422
- `test_auto_id`: no id supplied → 201, 32-char hex, `int(mid, 16)` succeeds, two calls differ

---

## Verification Results

```
.venv/bin/pytest tests/service/test_merchants.py -x -q
5 passed in 1.34s

.venv/bin/pytest tests/service -x -q
13 passed, 1 skipped in 1.47s
```

- All 5 merchant tests pass
- All prior health + lifespan tests still green
- Docker smoke placeholder still skipped (expected)

---

## Deviations from Plan

**1. [Rule 1 - Clarification] display_name → MerchantProfile.name field mapping**
- **Found during:** Task 8-02-01 implementation
- **Issue:** `CreateMerchantRequest` uses `display_name` (API naming) but `MerchantProfile` in the storage layer uses `name`. The plan did not document this mapping explicitly.
- **Fix:** Handler maps `body.display_name` → `MerchantProfile(name=body.display_name)`. Storage schema unchanged.
- **Files modified:** `routes/merchants.py`
- **Commit:** 51b5c6e

---

## Threat Surface Scan

T-5-01 (path traversal via merchant_id): mitigated as planned — `MerchantIdStr` Pydantic validation returns 422 before `MerchantStore.__init__` is ever called. Verified by `test_invalid_id_rejected_before_fs` which asserts zero `.sqlite` files in the merchants directory after a 422 response.

No new trust boundaries beyond what is documented in the plan's threat model.

---

## Known Stubs

None — all merchant tests fully implemented.

---

## Self-Check: PASSED

Files confirmed present:
- src/meshek_ml/service/routes/merchants.py — FOUND
- src/meshek_ml/service/schemas.py (CreateMerchantRequest added) — FOUND
- src/meshek_ml/service/app.py (merchants router wired) — FOUND
- tests/service/test_merchants.py (5 tests) — FOUND

Commits confirmed:
- 94a6ebb test(08-02): add failing tests for POST /merchants (RED) — FOUND
- 51b5c6e feat(08-02): implement POST /merchants with regex validation and auto-id (GREEN) — FOUND
