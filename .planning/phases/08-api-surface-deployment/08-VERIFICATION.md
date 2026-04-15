---
phase: 8
slug: api-surface-deployment
status: passed
must_haves_verified: 5
must_haves_total: 5
date: 2026-04-15
docker_smoke_run: 2026-04-15T07:07
human_verification:
  - test: "Deploy to Fly.io from a clean checkout: `fly deploy` in repo root"
    expected: "`fly deploy` succeeds; `fly open /health` returns 200 once a model bundle is in place (or 503 if using degraded-start)"
    why_human: "Actual cloud deployment requires a Fly.io account, flyctl, and a live cluster. Not blocking — Dockerfile/fly.toml are verified locally and the image runs end-to-end."
---

> **Update 2026-04-15:** Docker smoke test executed locally (`MESHEK_DOCKER_SMOKE=1 pytest`) and passed. End-to-end verification inside a running container confirmed: `GET /health` → 503 degraded, `POST /merchants` → 201, `POST /sales` with Hebrew free-text (`"20 עגבניות, 5 מלפפונים"`) → 200 `{accepted_rows: 2}`, `POST /recommend` → 200 `{reasoning_tier: "pooled_prior", confidence_score: 0.3}`. Two Dockerfile/test fixes landed in commit `dad8f6d` (README copy, project install layer, HTTPError handling). Status promoted to **passed**. Fly.io deploy remains as a documented manual step.


# Phase 8: API Surface & Deployment — Verification Report

**Phase Goal:** The meshek app can call all four endpoints over HTTP and the service can be deployed as a Docker container
**Verified:** 2026-04-15T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `GET /health` returns 200 confirming service alive and model loaded | VERIFIED | `routes/health.py:13-28` — sync handler reads `app.state.ml`, returns `JSONResponse` with `status_code=200` when loaded, 503 when degraded. `test_health.py::test_health_with_model` and `::test_health_degraded` both pass. |
| 2 | `POST /merchants` creates merchant with zero config, returns id | VERIFIED | `routes/merchants.py:27-39` — auto-generates `uuid4().hex` when `merchant_id` omitted, calls `MerchantStore.create_profile`, returns raw `MerchantProfile` with 201. `test_merchants.py` (5 tests) all pass including `test_auto_id` and `test_create_explicit_id`. |
| 3 | `POST /sales` accepts daily sales (including Hebrew free-text via parser) and stores it | VERIFIED | `routes/sales.py:30-100` — dual-shape handler; structured path builds DataFrame directly, free-text path calls `parse_sales_lines` via `request.app.state.catalog`. Partial-success semantics, all-fail returns 422 with error envelope. `test_sales.py` (7 tests) all pass including `test_hebrew_text` and `test_partial`. |
| 4 | `POST /recommend` returns per-product quantities with `reasoning_tier` and `confidence_score` | VERIFIED | `routes/recommend.py:24-33` — delegates to `request.app.state.engine.recommend(merchant_id)`. `test_recommend.py` (9 tests) all pass; `test_recommend_tier1/tier2/tier3` assert `reasoning_tier` and `confidence_score` in response body across all three tiers. |
| 5 | Service starts and handles requests inside a Docker container deployable to Railway or Fly.io | PARTIAL (human needed) | `Dockerfile` exists and is structurally correct: `python:3.12-slim`, `uv sync --locked --no-dev --extra service --extra runtime`, non-root `appuser`, `EXPOSE 8000`, `CMD [..., "--factory", ...]`, `HEALTHCHECK` accepting 200|503. `fly.toml` has `internal_port = 8000` matching Dockerfile CMD port. `.dockerignore` excludes `.planning`, `data`, `tests`, etc. Actual image build and container run require human verification (no Docker daemon available). |

**Score:** 4/5 truths fully automated-verified; SC-5 has structural evidence but cannot be closed without a Docker build.

---

### Deferred Items

None — all five success criteria are addressed within Phase 8.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/meshek_ml/service/app.py` | `create_app()` factory wrapping `build_lifespan()` with degraded-start | VERIFIED | 167 lines; sync `def create_app()`; `_build_engine_lifespan` wraps Phase 6 lifespan; catches `RuntimeError` → `app.state.ml = None`; includes all four routers; calls `register_exception_handlers` and adds `RequestContextMiddleware`. |
| `src/meshek_ml/service/routes/health.py` | `GET /health` endpoint reading `app.state.ml` | VERIFIED | Reads `getattr(request.app.state, "ml", None)`; returns `JSONResponse` with explicit status code 200/503. |
| `src/meshek_ml/service/routes/merchants.py` | `POST /merchants` sync handler | VERIFIED | `status_code=201`; `uuid.uuid4().hex` auto-id; `MerchantStore` context-manager; returns raw `MerchantProfile`. |
| `src/meshek_ml/service/routes/sales.py` | `POST /sales` dual-shape handler | VERIFIED | Structured path + free-text path via `parse_sales_lines`; reads `request.app.state.catalog` (migrated from `lru_cache` in plan 04); partial-success semantics; all-fail returns error envelope JSONResponse. |
| `src/meshek_ml/service/routes/recommend.py` | `POST /recommend` engine delegation | VERIFIED | Reads `request.app.state.engine`; calls `engine.recommend(body.merchant_id)`; no try/except (exceptions bubble to central handlers). |
| `src/meshek_ml/service/schemas.py` | All request/response Pydantic v2 models | VERIFIED | `MerchantIdStr` (Annotated regex), `HealthResponse`, `CreateMerchantRequest`, `SalesItem`, `SalesRequest` (model_validator), `SalesResponse`, `SkippedLine`, `RecommendRequest`, `SERVICE_VERSION = "1.1.0"`. |
| `src/meshek_ml/service/errors.py` | Exception handlers + error envelope + `JSONFormatter` | VERIFIED | `register_exception_handlers` maps 5 error classes to `{error:{code,message,details?}}`; `_safe_errors` strips non-JSON ctx; `JSONFormatter` stdlib-only. |
| `src/meshek_ml/service/middleware.py` | `RequestContextMiddleware` with per-request logging | VERIFIED | Generates `request_id`, sets `request.state.request_id`, emits structured log line with 5 required fields, adds `X-Request-ID` header. |
| `Dockerfile` | Single-stage python:3.12-slim, uv, non-root, CMD --factory | VERIFIED (static) | Structurally complete; actual build is human verification item. |
| `.dockerignore` | Excludes venv, tests, planning, data | VERIFIED | Lists `.venv`, `.git`, `.planning`, `notebooks`, `reports`, `outputs`, `data`, `academic`, `tests`, `**/__pycache__`, `**/*.pyc`, etc. |
| `fly.toml` | Fly.io config with internal_port=8000 | VERIFIED | `internal_port = 8000`, `primary_region = "ams"`, health check path `/health`, 512 MB VM, persistent volume mount. |
| `tests/service/conftest.py` | `data_dir`, `app_client`, `no_model_client` fixtures | VERIFIED | All three fixtures present with deferred imports; session-scoped `model_bundle_path` trains a real LightGBM bundle. |
| `tests/service/test_docker_smoke.py` | Env-guarded smoke test, skipped without `MESHEK_DOCKER_SMOKE=1` | VERIFIED | `@pytest.mark.skipif(not _SMOKE_ENABLED, ...)` + `@pytest.mark.integration`; collected, 1 skip confirmed in test run. |
| `pyproject.toml` | `service` extra includes `uvicorn[standard]>=0.44`; new `runtime` extra with `lightgbm>=4.0` | VERIFIED | Both entries present at lines 54 and 57-59 respectively; `all` extra includes `runtime`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `create_app()` | `service.lifespan.build_lifespan` | `asynccontextmanager` wrapping `async with phase6_lifespan(app)` | WIRED | `app.py:88-136`; RuntimeError caught → `app.state.ml = None` degraded-start |
| `routes/health.py` | `app.state.ml` | `getattr(request.app.state, "ml", None)` | WIRED | `health.py:19` |
| `routes/merchants.py` | `MerchantStore.create_profile` | context-manager per request | WIRED | `merchants.py:38-39`; `with MerchantStore(merchant_id) as store: return store.create_profile(profile)` |
| `routes/sales.py (structured)` | `MerchantStore.write_sales` | DataFrame with `[date, merchant_id, product, quantity]` | WIRED | `sales.py:43-57` |
| `routes/sales.py (free-text)` | `parsing.parse_sales_lines` | `request.app.state.catalog` loaded in lifespan | WIRED | `sales.py:60-66`; catalog from `app.state.catalog` (migrated plan 04) |
| `routes/recommend.py` | `RecommendationEngine.recommend` | `request.app.state.engine` built in lifespan | WIRED | `recommend.py:32-33`; engine built in `_build_engine_lifespan` for both happy and degraded paths |
| `app.py` | `errors.register_exception_handlers` | called in `create_app()` | WIRED | `app.py:157` |
| `app.py` | `RequestContextMiddleware` | `app.add_middleware(...)` | WIRED | `app.py:160` |
| `Dockerfile CMD` | `meshek_ml.service.app:create_app` | `--factory` flag | WIRED | `Dockerfile:44`; `fly.toml internal_port = 8000` matches `--port 8000` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `routes/health.py` | `ml` | `app.state.ml` set by Phase 6 `build_lifespan` | Yes — loaded LightGBM bundle | FLOWING |
| `routes/merchants.py` | `MerchantProfile` | `MerchantStore.create_profile` writes to SQLite | Yes — persisted and returned | FLOWING |
| `routes/sales.py` (free-text) | `catalog` | `request.app.state.catalog` set at startup via `load_catalog(DEFAULT_CATALOG_PATH)` | Yes — YAML-backed `ProductCatalog` | FLOWING |
| `routes/recommend.py` | `RecommendationResponse` | `engine.recommend(merchant_id)` → Phase 6 three-tier logic + MerchantStore | Yes — real DB query + LightGBM inference | FLOWING |

---

### Behavioral Spot-Checks

Test suite is the primary spot-check mechanism. All 36 tests passed, 1 skipped (Docker smoke).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Test suite: all service tests | `.venv/bin/python -m pytest tests/service -q` | `36 passed, 1 skipped in 2.40s` | PASS |
| Docker smoke test skipped without flag | Included in above run | `1 skipped` (test_docker_smoke.py::test_health) | PASS |
| Factory import | implicit via TestClient in all tests | No import errors | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| API-01 | 08-01 | `GET /health` returns service status | SATISFIED | `routes/health.py`; `test_health.py` 2 tests pass |
| API-02 | 08-02 | `POST /merchants` creates merchant | SATISFIED | `routes/merchants.py`; `test_merchants.py` 5 tests pass |
| API-03 | 08-03 | `POST /sales` accepts structured and Hebrew free-text | SATISFIED | `routes/sales.py`; `test_sales.py` 7 tests pass including Hebrew text path |
| API-04 | 08-04 | `POST /recommend` returns per-product recommendations | SATISFIED | `routes/recommend.py`; `test_recommend.py` 9 tests pass across all three tiers |
| INFRA-02 | 08-06 | Service runs in Docker container deployable to Railway/Fly.io | PARTIAL | `Dockerfile`, `.dockerignore`, `fly.toml` exist and are structurally correct; actual build/deploy requires human verification |

---

### Decision Coverage Audit (D-01 to D-25)

| Decision | Description | Status | Evidence |
|----------|-------------|--------|---------|
| D-01 | `uvicorn[standard]>=0.44` in service extra | VERIFIED | `pyproject.toml:54` |
| D-02 | `create_app()` factory wrapping `build_lifespan()` | VERIFIED | `app.py:140-166` |
| D-03 | Entry point `meshek_ml.service.app:create_app` | VERIFIED | `Dockerfile:44` CMD; module docstring line 3 |
| D-04 | Routes under `service/routes/` as APIRouters | VERIFIED | `routes/health.py`, `merchants.py`, `sales.py`, `recommend.py` all present |
| D-05 | All handlers sync `def` (no async) | VERIFIED | All four handlers are `def`, not `async def` |
| D-06 | Reuse existing pydantic models (`MerchantProfile`, `RecommendationResponse`) | VERIFIED | `merchants.py` response_model is `MerchantProfile`; `recommend.py` response_model is `RecommendationResponse` from `recommendation.schema` |
| D-07 | `POST /merchants` auto-generates `uuid4().hex` when id omitted | VERIFIED | `merchants.py:36` |
| D-08 | `POST /sales` accepts structured items OR free text; partial-success; all-fail → 422 | VERIFIED | `schemas.py:96-100` model_validator; `sales.py:43-100` |
| D-09 | `POST /recommend` accepts `{merchant_id}`, returns `RecommendationResponse` | VERIFIED | `schemas.py:115-122`; `recommend.py:25-33` |
| D-10 | `GET /health` returns `{status, model_loaded, version}`, 200 or 503 | VERIFIED | `health.py:13-28`; `schemas.py:31-37` |
| D-11 | Central exception handler maps domain errors to HTTP | VERIFIED | `errors.py:92-183`; 5 handlers registered |
| D-12 | Error envelope `{error:{code,message,details?}}`; success responses raw | VERIFIED | `errors.py:74-84`; all routes return raw pydantic models |
| D-13 | `MerchantIdStr` Pydantic regex enforces `^[A-Za-z0-9_-]{1,64}$` at edge | VERIFIED | `schemas.py:16`; applied to all three endpoints taking `merchant_id` |
| D-14 | Runtime config via `MESHEK_*` env vars | VERIFIED | `Dockerfile:31-37` sets all five env vars with defaults |
| D-15 | No auth in v1.1 | VERIFIED | No auth code present in any route or middleware |
| D-16 | Single-stage Dockerfile, `python:3.12-slim`, uv, service+runtime extras only | VERIFIED | `Dockerfile:1-12` |
| D-17 | `/app` layout, non-root `appuser`, `EXPOSE 8000` | VERIFIED | `Dockerfile:14-28` |
| D-18 | `HEALTHCHECK` hits `GET /health` every 30s | VERIFIED | `Dockerfile:41-42` — polls `/health`, accepts 200|503 |
| D-19 | Model bundle path `/app/models/lightgbm_v1.bundle`, override via `MESHEK_MODEL_PATH` | VERIFIED | `Dockerfile:33`; `MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle` |
| D-20 | `.dockerignore` excludes dev/test/data artifacts | VERIFIED | `.dockerignore` lists `.venv`, `.planning`, `data`, `tests`, `notebooks`, `reports`, etc. |
| D-21 | `fly.toml` for Fly.io; Railway uses same Dockerfile | VERIFIED | `fly.toml` present; Railway fallback documented in 08-06-SUMMARY.md |
| D-22 | No CI/CD pipeline in this phase | VERIFIED | No `.github/workflows` added |
| D-23 | Structured JSON logs per request with `{request_id, method, path, status, duration_ms}` | VERIFIED | `middleware.py:46-54`; `JSONFormatter` in `errors.py:191-219`; `test_errors.py::test_structured_log_line` passes |
| D-24 | Integration tests under `tests/service/` using `TestClient` | VERIFIED | 36 tests passing covering all four endpoints, all error envelopes, all three tiers |
| D-25 | Docker smoke test guarded by `MESHEK_DOCKER_SMOKE=1` | VERIFIED | `test_docker_smoke.py:21-23`; `@pytest.mark.skipif(not _SMOKE_ENABLED, ...)`; 1 skip confirmed |

---

### Security Check Summary

**T-5-01: merchant_id path traversal guard**

`MerchantIdStr = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]` is applied to `merchant_id` on all three endpoints that accept it:
- `CreateMerchantRequest.merchant_id` (`POST /merchants`) — `schemas.py:56`
- `SalesRequest.merchant_id` (`POST /sales`) — `schemas.py:91`
- `RecommendRequest.merchant_id` (`POST /recommend`) — `schemas.py:122`

`test_merchants.py::test_invalid_id_rejected_before_fs` explicitly asserts zero SQLite files in `data_dir` after a 422, proving the guard fires before `MerchantStore.__init__` is called.

**Error envelope consistency (D-12)**

All error paths return `{error: {code, message, details?}}`:
- `errors.py:74-84` — `_error_response()` builder used by all exception handlers
- `sales.py:85-94` — all-fail path uses direct `JSONResponse` with the same shape (fixed in plan 05)
- `test_errors.py` (7 tests) verifies envelope on 404, 422, 503, 500 paths

**Information disclosure (T-8-03, T-8-10)**

Stack traces logged server-side with `exc_info=True` only. Generic 500 responses return only opaque `request_id` (32-char hex); no exception message surfaces.

---

### Anti-Patterns Found

No blockers or warnings found. Stub scan results:

| File | Pattern | Verdict |
|------|---------|---------|
| `routes/recommend.py` | `engine.recommend(body.merchant_id)` — one-liner body | NOT A STUB — delegates to Phase 6 engine with real three-tier logic; 9 tests verify real data flows through |
| `routes/sales.py` | `parse_sales_lines(lines, catalog)` | NOT A STUB — real Phase 7 catalog is on `app.state.catalog`; `test_hebrew_text` verifies rows are persisted |

---

### Human Verification Required

#### 1. Docker Image Build and Container Run

**Test:** From the repo root, run:
```
docker build -t meshek-ml-test .
docker run --rm -p 18000:8000 -e MESHEK_DATA_DIR=/tmp/merchants meshek-ml-test
curl http://localhost:18000/health
```
**Expected:** `docker build` completes without error. Container starts within 15 seconds. `curl` returns HTTP 200 or 503 with body `{"status":"ok","model_loaded":false,"version":"1.1.0"}` (503/false because no model bundle is baked in by default — degraded-start contract).
**Why human:** No Docker daemon accessible during automated verification. The smoke test scaffolding (`tests/service/test_docker_smoke.py`) is fully implemented and will run this exact sequence when `MESHEK_DOCKER_SMOKE=1` is set, but that requires a running Docker daemon.

#### 2. Fly.io Deployment

**Test:** With `flyctl` installed and authenticated, run `fly deploy` from the repo root.
**Expected:** Deploy succeeds; `fly open /health` returns 503 (degraded) or 200 (if a model bundle is placed at `/app/models/lightgbm_v1.bundle`). Volume mount at `/var/lib/meshek/merchants` persists across restarts.
**Why human:** Requires a Fly.io account, live cluster, and `flyctl`. Cannot be automated in code-only verification.

---

### Gaps Summary

No gaps. All automated checks pass. The only open item is the Docker image build/container run and Fly.io deployment, which are human verification items per the phase specification ("if Docker image can only be validated manually by a human running `docker build`, list it under `human_verification`").

The 36-test suite (36 passed, 1 skipped) provides comprehensive coverage:
- API-01 through API-04: all four endpoints verified end-to-end with real storage and real recommendation engine
- Error envelope shape: verified on 404, 422, 503, 500 paths
- Security: T-5-01 path-traversal guard verified with filesystem I/O assertion
- Degraded-start: Tier 1/2 verified in no-model mode; Tier 3 503 verified
- Hebrew parsing integration: end-to-end through Phase 7 parser with real catalog
- Docker smoke test: collected and correctly skipped without `MESHEK_DOCKER_SMOKE=1`

---

## VERIFICATION COMPLETE

_Verified: 2026-04-15_
_Verifier: Claude (gsd-verifier)_
