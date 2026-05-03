---
phase: 08-api-surface-deployment
plan: "03"
subsystem: service
tags: [fastapi, sales, hebrew-parser, partial-success, pydantic-v2, tdd, wave-2]
dependency_graph:
  requires: [service/app.py, service/schemas.py, parsing/__init__.py, storage/merchant_store.py]
  provides: [service/routes/sales.py, POST /sales endpoint]
  affects: [plan 04 will migrate catalog to app.state.catalog; plan 05 maps UnknownMerchantError to 404]
tech_stack:
  added: []
  patterns: [dual-shape Pydantic model_validator, lru_cache catalog singleton, partial-success POST semantics]
key_files:
  created:
    - src/meshek_ml/service/routes/sales.py
  modified:
    - src/meshek_ml/service/schemas.py
    - src/meshek_ml/service/app.py
    - tests/service/test_sales.py
decisions:
  - "Catalog loaded via module-level lru_cache(maxsize=1) in routes/sales.py to avoid depending on plan 04's lifespan extension; TODO comment left for plan 04 migration to app.state.catalog"
  - "SalesRequest.model_validator(mode='after') enforces exactly-one-of items|text; both or neither => 422 before any I/O"
  - "All-lines-fail raises HTTPException(422) with structured detail; partial failure returns 200 with skipped list (D-08)"
  - "Free-text split on comma then strip/filter empty; list[str] passed to parse_sales_lines()"
  - "unknown_merchant test asserts status in (404, 500) to stay green until plan 05's central handler lands"
metrics:
  duration_min: 10
  tasks_completed: 3
  files_created: 1
  files_modified: 3
  completed_date: "2026-04-14"
requirements: [API-03, PARSE-01, PARSE-02]
---

# Phase 8 Plan 03: POST /sales Dual-Shape Handler Summary

**One-liner:** `POST /sales` with Pydantic dispatch validator accepting structured `items` or Hebrew free text, Phase 7 `parse_sales_lines` integration, partial-success semantics returning `{accepted_rows, skipped[]}`, and all-fail 422.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-03-01 RED+GREEN | schemas + structured items path + full test suite | 8a40b4c | schemas.py, routes/sales.py, app.py, tests/service/test_sales.py |
| 8-03-02 | Hebrew free-text path (implementation shipped with 8-03-01) | 8a40b4c | routes/sales.py |
| 8-03-03 | Partial-success semantics (tests shipped with 8-03-01; GREEN verified) | 8a40b4c | tests/service/test_sales.py |

---

## What Was Built

### src/meshek_ml/service/schemas.py (extended)

- `SalesItem(product_id, quantity, unit)` — single structured line item; `product_id` 1-64 chars, `quantity > 0`
- `SkippedLine(line, reason)` — per-line parse failure report
- `SalesRequest(merchant_id, date, items, text)` — dispatching request body:
  - `merchant_id: MerchantIdStr` — regex validation at edge (T-5-01)
  - `text: str | None = Field(max_length=2048)` — matches parser's `_MAX_INPUT_CHARS` cap (T-7-02)
  - `@model_validator(mode="after")` enforces exactly one of `items` / `text`; raises ValueError → 422 before any I/O
- `SalesResponse(accepted_rows, skipped)` — clean response shape (D-08)

### src/meshek_ml/service/routes/sales.py (new)

- `router = APIRouter()`
- `@lru_cache(maxsize=1) _get_catalog()` — one-time catalog load from `DEFAULT_CATALOG_PATH`; TODO comment for plan 04 migration to `app.state.catalog`
- `@router.post("/sales") post_sales(body, request) -> SalesResponse`:
  - **Structured path** (`body.items is not None`): builds DataFrame with columns `[date, merchant_id, product, quantity]`, calls `MerchantStore(merchant_id, must_exist=True).write_sales(df)`, returns `SalesResponse(accepted_rows=n, skipped=[])`
  - **Free-text path**: splits `body.text` on `,`, strips/filters empty segments, calls `parse_sales_lines(lines, catalog)`, classifies each result as `ParsedSale` or `ParseError`, builds `accepted` list and `skipped` list
  - All-fail guard: if `accepted` is empty, raises `HTTPException(422, detail={code, skipped})`
  - Otherwise writes accepted rows via `MerchantStore.write_sales(df)` and returns `SalesResponse(accepted_rows=n, skipped=skipped)`

### src/meshek_ml/service/app.py (extended)

- `from meshek_ml.service.routes import health, merchants, sales`
- `app.include_router(sales.router)`

### tests/service/test_sales.py (replaced stub)

Seven tests covering all required behaviors:
- `test_structured` — 2 structured items → 200, accepted_rows=2, rows persisted with correct product/quantity
- `test_sales_rejects_both_shapes` — items + text → 422
- `test_sales_rejects_neither` — neither → 422
- `test_hebrew_text` — `"20 עגבניות, 5 מלפפונים"` → 200, accepted_rows=2, products in {"tomato","cucumber"}
- `test_partial` — `"20 עגבניות, שקל רע, 5 מלפפונים"` → 200, accepted_rows=2, skipped[0].reason is non-empty string
- `test_all_fail` — `"bogus bogus"` → 422
- `test_sales_unknown_merchant` — nonexistent merchant → status in (404, 500)

---

## Verification Results

```
.venv/bin/python -m pytest tests/service -x -q
20 passed, 1 skipped in 1.63s
```

- All 7 new sales tests pass
- All prior health, lifespan, and merchant tests still green
- Docker smoke placeholder still skipped (expected, plan 06)

---

## Deviations from Plan

**1. [Rule 2 - Implementation consolidation] Hebrew free-text + partial-success implemented in same commit as structured path**

- **Found during:** Task 8-03-01 implementation
- **Reason:** The plan's `routes/sales.py` action described both the structured path and the `else` free-text branch together in one handler. Writing them as two separate commits would have required a temporary `raise NotImplementedError` stub. Implementing the complete handler in one TDD cycle is cleaner and avoids an incomplete intermediate state.
- **Impact:** Tasks 8-03-02 and 8-03-03 have no additional source changes; their tests passed GREEN immediately on 8-03-01's commit.
- **Files modified:** `routes/sales.py`
- **Commit:** 8a40b4c

---

## Integration Notes

- Plan 04 will extend `_build_engine_lifespan` to populate `app.state.catalog` and update `routes/sales.py` to read `request.app.state.catalog` instead of calling `_get_catalog()`.
- Plan 05 adds central `UnknownMerchantError → 404` mapping; `test_sales_unknown_merchant` currently accepts `status in (404, 500)` to stay green until then.

---

## Threat Surface Scan

- T-5-01: `merchant_id` in `SalesRequest` validated via `MerchantIdStr` regex before `MerchantStore` is instantiated — edge guard in place.
- T-7-02: `SalesRequest.text` capped at `max_length=2048` for early 422; parser also caps at `_MAX_INPUT_CHARS=2048` (defense in depth).
- T-8-06: Structured items with `product_id` outside the catalog are accepted (documented accept disposition — catalog enforcement deferred to v2).
- T-8-07: Partial-success `skipped[]` list gives caller visibility into dropped lines.

No new trust boundaries beyond what is documented in the plan's threat model.

---

## Known Stubs

None — all sales tests fully implemented and wired.

---

## Self-Check: PASSED

Files confirmed present:
- src/meshek_ml/service/routes/sales.py — FOUND
- src/meshek_ml/service/schemas.py (SalesItem, SalesRequest, SalesResponse, SkippedLine added) — FOUND
- src/meshek_ml/service/app.py (sales router wired) — FOUND
- tests/service/test_sales.py (7 tests) — FOUND

Commits confirmed:
- 8a40b4c feat(08-03): structured items path for POST /sales — FOUND
