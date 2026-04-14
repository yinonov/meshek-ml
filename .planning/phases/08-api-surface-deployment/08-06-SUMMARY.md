---
phase: 08-api-surface-deployment
plan: "06"
subsystem: infra
tags: [docker, fly.toml, deployment, smoke-test, uv, tdd, wave-3, infra-02, d16, d17, d18, d19, d20, d21, d25]
dependency_graph:
  requires: [service/app.py, pyproject.toml, uv.lock, configs/, models/]
  provides: [Dockerfile, .dockerignore, fly.toml, tests/service/test_docker_smoke.py]
  affects: [deployment pipeline; fly.toml references Dockerfile CMD; smoke test validates container health]
tech_stack:
  added:
    - "ghcr.io/astral-sh/uv:latest (Docker COPY --from for uv binary)"
    - "python:3.12-slim (base image)"
  patterns:
    - single-stage-docker-with-uv
    - non-root-container-user
    - env-guarded-integration-test
    - degraded-start-healthcheck
key_files:
  created:
    - Dockerfile
    - .dockerignore
    - fly.toml
    - tests/service/test_docker_smoke.py
  modified: []
decisions:
  - "HEALTHCHECK accepts 200|503 (alive) while fly.toml [[http_service.checks]] requires 200 (healthy) — asymmetric signals give operators two distinct readings"
  - "models/ COPY is best-effort: .gitkeep present at build time; degraded-start contract handles missing bundle at runtime"
  - "No railway.json — Railway auto-detects Dockerfile; documented as one-paragraph fallback in this summary"
  - "pytest.mark.skipif used over runtime pytest.skip() so collection itself reflects skip reason"
metrics:
  duration_min: 15
  tasks_completed: 2
  files_created: 4
  files_modified: 0
  completed_date: "2026-04-15"
requirements: [INFRA-02]
---

# Phase 8 Plan 06: Dockerfile + Fly.io Config + Docker Smoke Test Summary

**One-liner:** Single-stage `python:3.12-slim` image built with `uv sync --locked --no-dev --extra service --extra runtime`; non-root `appuser`; HEALTHCHECK accepting 200|503; `fly.toml` targeting Fly.io `ams` region with 512 MB VM and persistent mount; env-guarded smoke test that builds and curls `/health`.

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 8-06-01 | Dockerfile + .dockerignore + fly.toml | ee597e4 | Dockerfile, .dockerignore, fly.toml |
| 8-06-02 | Env-guarded Docker smoke test | 2294b5e | tests/service/test_docker_smoke.py |

---

## What Was Built

### Dockerfile

Single-stage image based on `python:3.12-slim`:

- Copies `uv` binary from `ghcr.io/astral-sh/uv:latest` — no separate uv install step.
- Installs only `service` + `runtime` extras (`--locked --no-dev`) — torch, stable-baselines3, flwr, streamlit, and u8darts are excluded.
- Copies `src/`, `configs/`, and `models/` (models may contain only `.gitkeep` at build time; degraded-start contract handles the missing-bundle case at runtime).
- Creates `/var/lib/meshek/merchants`, adds non-root `appuser` (system, no home dir), chowns both directories.
- Sets `ENV` defaults for all `MESHEK_*` config vars and extends `PATH` to `.venv/bin`.
- `HEALTHCHECK` polls `http://localhost:8000/health` every 30s; accepts HTTP 200 or 503 as "alive" — a degraded (503) container is still responsive, only Fly.io's platform check enforces 200.
- `CMD` launches uvicorn with `--factory` pointing at `meshek_ml.service.app:create_app`.

### .dockerignore

Excludes `.venv`, `.git`, `.gitignore`, `.planning`, `notebooks`, `reports`, `outputs`, `data`, `academic`, `tests`, `**/__pycache__`, `**/*.pyc`, `.pytest_cache`, `.ruff_cache`, `.DS_Store`, `*.egg-info` — planning notes and raw merchant data never ship in the image (T-8-14 mitigated).

### fly.toml

- `app = "meshek-ml"`, `primary_region = "ams"` (closest Fly.io region to Israel).
- `[build] dockerfile = "Dockerfile"`.
- `[http_service]`: `internal_port = 8000`, `force_https = true`, auto-stop/start machines, `min_machines_running = 0`.
- `[[http_service.checks]]`: path `/health`, 30s interval, 5s timeout, 15s grace — **requires HTTP 200** (stricter than the Dockerfile HEALTHCHECK which accepts 503).
- `[[vm]]`: 512 MB, 1 CPU.
- `[[mounts]]`: persistent volume `meshek_data` → `/var/lib/meshek/merchants`, 1 GB initial size.

### tests/service/test_docker_smoke.py

Replaces the Wave 0 stub with a real implementation:

- `@pytest.mark.skipif(not _SMOKE_ENABLED, ...)` — skipped unless `MESHEK_DOCKER_SMOKE=1`.
- `@pytest.mark.integration` — excluded from `-m "not integration"` runs.
- `test_health()`: runs `docker build -t meshek-ml-smoke:test .` (10-minute timeout for cold cache), starts container with `-p 18000:8000 -e MESHEK_DATA_DIR=/tmp/merchants`, polls `http://localhost:18000/health` for up to 15 seconds with 1-second backoff, asserts `status in (200, 503)`, cleans up with `docker rm -f` in `finally`.

---

## Deploy to Railway (fallback)

`railway link` the repo in the Railway dashboard; Railway will detect `Dockerfile` automatically. Set `MESHEK_DATA_DIR=/var/lib/meshek/merchants`, `MESHEK_MODEL_PATH=/app/models/lightgbm_v1.bundle`, `MESHEK_LOG_LEVEL=info` in the service's Variables tab. Add a persistent volume mounted at `/var/lib/meshek/merchants`. Deploy. Confirm `GET https://<service>.up.railway.app/health` returns 200 once a model bundle is uploaded.

---

## Verification Results

```
.venv/bin/pytest tests/service -x -q
36 passed, 1 skipped in 2.38s
```

- Smoke test collected without errors (`pytest --collect-only`)
- Smoke test skipped (as expected) without `MESHEK_DOCKER_SMOKE=1`
- All 36 prior service tests still green
- Actual Docker build + container run deferred to manual operator verification (per plan scope — no Docker daemon access during execution)

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information-disclosure | .dockerignore | Verified excludes .planning/, data/, outputs/, academic/, notebooks/, reports/, tests/ — planning notes and raw merchant data excluded from image (T-8-14 mitigated) |
| threat_flag: privilege-escalation | Dockerfile | Non-root appuser confirmed (USER appuser, --system --no-create-home) — T-8-15 mitigated |
| threat_flag: dependency-drift | Dockerfile | uv sync --locked enforces lock consistency — T-8-16 mitigated |

No new trust boundaries introduced beyond those documented in the plan's threat model.

---

## Known Stubs

None — all artifacts fully implemented.

---

## Self-Check: PASSED
