---
phase: 08-api-surface-deployment
plan: "01"
subsystem: service
tags: [fastapi, uvicorn, health-endpoint, degraded-start, tdd, wave-0]
dependency_graph:
  requires: [service/lifespan.py, service/state.py]
  provides: [service/app.py, service/routes/health.py, service/schemas.py, tests/service/conftest.py]
  affects: [plans 02-06 all import create_app from service/app.py]
tech_stack:
  added: [uvicorn[standard]>=0.44, lightgbm>=4.0 (runtime extra)]
  patterns: [FastAPI factory pattern, asynccontextmanager degraded-start wrapper, TDD red-green]
key_files:
  created:
    - src/meshek_ml/service/app.py
    - src/meshek_ml/service/schemas.py
    - src/meshek_ml/service/routes/__init__.py
    - src/meshek_ml/service/routes/health.py
    - tests/service/test_health.py
    - tests/service/test_merchants.py
    - tests/service/test_sales.py
    - tests/service/test_recommend.py
    - tests/service/test_errors.py
    - tests/service/test_docker_smoke.py
    - uv.lock
  modified:
    - pyproject.toml
    - tests/service/conftest.py
decisions:
  - "Degraded-start: create_app() catches RuntimeError from build_lifespan() and yields with app.state.ml=None so the app still boots and GET /health returns 503"
  - "SERVICE_VERSION=1.1.0 constant in schemas.py is the single source of truth for version in health response"
  - "Deferred imports in conftest.py fixtures so pytest --collect-only works before app.py exists"
metrics:
  duration_min: 15
  tasks_completed: 2
  files_created: 11
  files_modified: 2
  completed_date: "2026-04-15"
requirements: [API-01]
---

# Phase 8 Plan 01: Foundation, Deps, Health Endpoint Summary

**One-liner:** FastAPI `create_app()` factory with degraded-start lifespan wrapping Phase 6 `build_lifespan()`, `GET /health` returning 200/503, and full `tests/service/` Wave 0 scaffolding.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-01-01 | Wave 0 scaffolding — deps, test stubs, fixtures | d3094d1 | pyproject.toml, uv.lock, conftest.py, 6 stub test files |
| 8-01-02 RED | Failing health tests | 374dee9 | tests/service/test_health.py |
| 8-01-02 GREEN | create_app() + /health implementation | d0e0bcc | app.py, schemas.py, routes/__init__.py, routes/health.py |

---

## What Was Built

### Dependency changes (pyproject.toml)
- `service` extra now includes `uvicorn[standard]>=0.44` (D-01)
- New `runtime` extra with `lightgbm>=4.0` (required for `joblib.load()` of `LGBMRegressor` in the Docker image)
- `all` extra updated to include `runtime`
- `uv.lock` regenerated; added: httptools, uvloop, watchfiles, websockets, python-dotenv

### src/meshek_ml/service/schemas.py
- `MerchantIdStr = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]` — shared regex-validated type for plans 02-04 (D-13)
- `HealthResponse(status, model_loaded, version)` Pydantic v2 model
- `SERVICE_VERSION = "1.1.0"` constant

### src/meshek_ml/service/routes/health.py
- `GET /health` sync handler reading `request.app.state.ml`
- Returns `JSONResponse` with explicit status code: 200 when model loaded, 503 when degraded
- No stack trace in response body (T-8-03 mitigated)

### src/meshek_ml/service/app.py
- `create_app() -> FastAPI` — sync `def` factory (Pitfall 4: uvicorn `--factory` requires sync)
- `_build_engine_lifespan()` wraps Phase 6 `build_lifespan()` in degraded-start contract:
  - Success path: `async with phase6_lifespan(app)` populates `app.state.ml`
  - `RuntimeError` path: warning logged with `exc_info=True` server-side only, `app.state.ml = None`, service still boots and serves 503 on `/health`
- Includes `health.router`

### tests/service/conftest.py (extended)
Three new fixtures added alongside existing `model_bundle_path`:
- `data_dir(tmp_path, monkeypatch)` — creates merchants subdir, sets `MESHEK_DATA_DIR`
- `app_client(model_bundle_path, data_dir, monkeypatch)` — full-model TestClient
- `no_model_client(data_dir, monkeypatch, tmp_path)` — degraded-mode TestClient
All use deferred imports (`from meshek_ml.service.app import create_app` inside fixture body).

### Wave 0 stub test files
Six files created so `pytest --collect-only` succeeds for all downstream plans:
`test_health.py`, `test_merchants.py`, `test_sales.py`, `test_recommend.py`, `test_errors.py`, `test_docker_smoke.py`

---

## Verification Results

```
.venv/bin/python -m pytest tests/service -x -q
8 passed, 1 skipped in 1.64s
```

- `test_health_with_model` — PASSED (200, model_loaded=true, version=1.1.0)
- `test_health_degraded` — PASSED (503, model_loaded=false, version=1.1.0)
- `test_docker_smoke_placeholder` — SKIPPED (MESHEK_DOCKER_SMOKE not set, as expected)
- All 6 Phase 6 lifespan tests — PASSED

Import smoke check:
```
python -c "from meshek_ml.service.app import create_app; app = create_app()"
# routes: ['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/health']
```

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries beyond what is documented in the plan's threat model.

- T-8-01 (model path traversal): inherited from Phase 6 `load_model_bundle` — no new surface.
- T-8-02 (degraded-start masks broken bundle): mitigated — 503 visible to orchestrators.
- T-8-03 (stack trace in response): mitigated — `exc_info=True` server-side only, no error body on `/health`.

---

## Known Stubs

| File | Note |
|------|------|
| tests/service/test_merchants.py | Stub only; implemented in plan 02 |
| tests/service/test_sales.py | Stub only; implemented in plan 03 |
| tests/service/test_recommend.py | Stub only; implemented in plan 04 |
| tests/service/test_errors.py | Stub only; implemented in plan 05 |
| tests/service/test_docker_smoke.py | Placeholder test; full body added in plan 06 |

These stubs are intentional Wave 0 scaffolding; each will be replaced by its respective plan.

---

## Self-Check: PASSED

Files confirmed present:
- src/meshek_ml/service/app.py — FOUND
- src/meshek_ml/service/schemas.py — FOUND
- src/meshek_ml/service/routes/__init__.py — FOUND
- src/meshek_ml/service/routes/health.py — FOUND
- tests/service/conftest.py — FOUND (modified)
- tests/service/test_health.py — FOUND

Commits confirmed:
- d3094d1 feat(08-01): wave 0 scaffolding — FOUND
- 374dee9 test(08-01): add failing tests — FOUND
- d0e0bcc feat(08-01): create_app() factory — FOUND
