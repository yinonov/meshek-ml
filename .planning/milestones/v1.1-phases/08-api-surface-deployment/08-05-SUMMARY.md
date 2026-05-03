---
phase: 08-api-surface-deployment
plan: "05"
subsystem: service
tags: [fastapi, error-handling, structured-logging, middleware, tdd, wave-3, d11, d12, d23]
dependency_graph:
  requires: [service/app.py, service/routes/recommend.py, service/routes/sales.py, storage/merchant_store.py, recommendation/engine.py, forecasting/schema.py]
  provides: [service/errors.py, service/middleware.py, register_exception_handlers, RequestContextMiddleware, JSONFormatter]
  affects: [all routes now emit structured log lines and return error envelopes; plan 06 Dockerfile inherits this logging setup]
tech_stack:
  added: []
  patterns: [centralized-exception-handlers, error-envelope, structured-json-logging, request-id-middleware, idempotent-logging-config]
key_files:
  created:
    - src/meshek_ml/service/errors.py
    - src/meshek_ml/service/middleware.py
  modified:
    - src/meshek_ml/service/app.py
    - src/meshek_ml/service/routes/sales.py
    - tests/service/test_errors.py
    - tests/service/test_recommend.py
    - tests/service/test_sales.py
decisions:
  - "register_exception_handlers uses _safe_errors() to strip non-JSON-serializable ctx values (pydantic v2 attaches raw exception objects in ctx dicts)"
  - "All-fail 422 in routes/sales.py changed from HTTPException to direct JSONResponse envelope for D-12 consistency"
  - "test_500_envelope_opaque_request_id patches RecommendationEngine.recommend (not the route function) because FastAPI captures the endpoint reference at route registration time"
  - "_configure_logging uses module-level _LOGGING_CONFIGURED flag as guard since logging.basicConfig force=False is a no-op after first call but multiple test fixtures call create_app()"
  - "RequestContextMiddleware: exception handlers run inside FastAPI's exception handling middleware, so call_next returns a response even on errors; middleware always captures the final status"
metrics:
  duration_min: 25
  tasks_completed: 2
  files_created: 2
  files_modified: 5
  completed_date: "2026-04-14"
requirements: []
---

# Phase 8 Plan 05: Centralized Error Handling + Structured Logging Summary

**One-liner:** `register_exception_handlers(app)` mapping five error classes to the `{error:{code,message,details?}}` envelope; `RequestContextMiddleware` emitting per-request structured JSON log lines with `request_id`, `method`, `path`, `status`, `duration_ms`; all forward-looking assertions from plans 03/04 tightened.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-05-01 RED | Failing tests for all 6 envelope cases + structured log line | e574037 | tests/service/test_errors.py |
| 8-05-01 GREEN | errors.py + middleware.py + app.py wiring + assertion tightening | e574037 | errors.py, middleware.py, app.py, routes/sales.py, test_recommend.py, test_sales.py |
| 8-05-02 | test_unknown_merchant (included in above commit) | e574037 | tests/service/test_errors.py |

---

## What Was Built

### src/meshek_ml/service/errors.py (new)

- `_safe_errors(errors)` — strips non-JSON-serializable `ctx` values from pydantic error dicts (Python exception objects in `ctx.error`)
- `_error_response(code, message, status, details=None) -> JSONResponse` — builds canonical `{"error": {"code", "message", "details?"}}` envelope
- `register_exception_handlers(app)` registering five async handlers:
  - `UnknownMerchantError` → 404 `merchant_not_found`
  - `RequestValidationError` → 422 `validation_error` with sanitized `details` (§Pitfall 2 — distinct from pydantic `ValidationError`)
  - `ValidationError` → 422 `validation_error` with sanitized `details`
  - `SchemaValidationError` → 422 `schema_validation_error`
  - `RuntimeError` → 503 `model_unavailable` if message contains `"Tier 3 requires a loaded model"`, else 500 with opaque `request_id`
  - `Exception` → 500 with opaque `request_id`, `exc_info=True` logged server-side (T-8-10)
- `class JSONFormatter(logging.Formatter)` — stdlib-only JSON log formatter merging `extra` fields into a flat JSON line

### src/meshek_ml/service/middleware.py (new)

- `RequestContextMiddleware(BaseHTTPMiddleware)`:
  - Generates `request_id = uuid.uuid4().hex` per request
  - Sets `request.state.request_id`
  - Adds `X-Request-ID` response header (T-8-13)
  - Emits `logger.info("request", extra={request_id, method, path, status, duration_ms})` after each response

### src/meshek_ml/service/app.py (extended)

- `_configure_logging()` — one-time JSON logging setup with `_LOGGING_CONFIGURED` module guard
- `create_app()` now calls:
  1. `_configure_logging()`
  2. `register_exception_handlers(app)`
  3. `app.add_middleware(RequestContextMiddleware)`

### src/meshek_ml/service/routes/sales.py (fixed)

- All-fail path replaced `HTTPException(422)` with direct `JSONResponse` using the error envelope (D-12 consistency — HTTPException produces `{"detail": ...}` not `{"error": ...}`)

### tests/service/test_errors.py (replaced stub)

Seven tests covering all required behaviors:
- `test_404_envelope` — unknown merchant POST /sales → 404 + envelope
- `test_422_envelope` — invalid `merchant_id` POST /merchants → 422 + envelope
- `test_422_envelope_missing_field` — empty body POST /recommend → 422 + envelope (RequestValidationError path)
- `test_503_envelope` — Tier 3 no-model → 503 + `code: model_unavailable`
- `test_500_envelope_opaque_request_id` — patched engine raises `ValueError("boom")` → 500, `"boom"` not in body, `request_id` is 32-char hex
- `test_structured_log_line` — GET /health → middleware log record has all 5 required fields
- `test_unknown_merchant` (Task 8-05-02) — POST /recommend for unknown merchant → 404 + `merchant_not_found` envelope

### Tightened assertions (plans 03/04)

- `test_sales.py::test_all_fail` → `status == 422` + `body["error"]["code"] == "all_lines_failed"`
- `test_sales.py::test_sales_unknown_merchant` → `status == 404` + `body["error"]["code"] == "merchant_not_found"`
- `test_recommend.py::test_missing_model` → `status == 503` + `body["error"]["code"] == "model_unavailable"`

---

## Verification Results

```
source .venv/bin/activate && python -m pytest tests/service -x -q
36 passed, 1 skipped in 2.47s
```

- All 7 new error-envelope tests pass
- All prior health, lifespan, merchant, sales, recommend tests still green
- Docker smoke placeholder still skipped (expected, plan 06)

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] pydantic v2 ctx.error non-JSON-serializable**
- **Found during:** Task 8-05-01 GREEN (test_sales_rejects_both_shapes failed with TypeError)
- **Issue:** `exc.errors()` from `RequestValidationError` returns dicts with `ctx: {"error": ValueError(...)}` — the raw exception object is not JSON-serializable
- **Fix:** Added `_safe_errors()` helper that stringifies non-primitive values in `ctx` dicts before passing to `JSONResponse`
- **Files modified:** `src/meshek_ml/service/errors.py`
- **Commit:** e574037

**2. [Rule 2 - Missing consistency] All-fail 422 in sales.py used HTTPException not envelope**
- **Found during:** Task 8-05-01 review of sales route
- **Issue:** `HTTPException(422)` produces `{"detail": ...}` format (FastAPI default), bypassing the error envelope from D-12
- **Fix:** Replaced with direct `JSONResponse` using `{"error": {"code": "all_lines_failed", ...}}` envelope
- **Files modified:** `src/meshek_ml/service/routes/sales.py`
- **Commit:** e574037

**3. [Rule 1 - Bug] test_500 monkeypatch target wrong**
- **Found during:** Task 8-05-01 RED
- **Issue:** `monkeypatch.setattr(rec_module, "post_recommend", _raise)` does not affect what FastAPI calls — FastAPI captures the endpoint function reference at route registration time (before test patches it)
- **Fix:** Patch `RecommendationEngine.recommend` instead, which is what the route handler invokes at request time
- **Files modified:** `tests/service/test_errors.py`
- **Commit:** e574037

---

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information-disclosure | service/errors.py | All handlers verified to exclude exception messages and stack traces from response bodies; only opaque `request_id` returned for 500s (T-8-10 mitigated) |

No new trust boundaries introduced.

---

## Known Stubs

None — all error handlers fully implemented and verified.

---

## Self-Check: PASSED
