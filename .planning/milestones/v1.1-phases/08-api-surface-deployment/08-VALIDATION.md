---
phase: 8
slug: api-surface-deployment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/service -x -q` |
| **Full suite command** | `uv run pytest tests/service` |
| **Estimated runtime** | ~30 seconds (excluding Docker smoke test) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/service -x -q`
- **After every plan wave:** Run `uv run pytest tests/service`
- **Before `/gsd-verify-work`:** Full suite must be green; Docker smoke test must pass at least once
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 8-01-01 | 01 | 0 | — | — | Wave 0: test scaffolding | infra | `uv run pytest tests/service --collect-only` | ❌ W0 | ⬜ pending |
| 8-01-02 | 01 | 1 | API-01 | — | `/health` returns 200 when model loaded | unit | `uv run pytest tests/service/test_health.py -x` | ❌ W0 | ⬜ pending |
| 8-01-03 | 01 | 1 | API-01 | — | `/health` returns 503 when model missing | unit | `uv run pytest tests/service/test_health.py::test_health_degraded -x` | ❌ W0 | ⬜ pending |
| 8-02-01 | 02 | 1 | API-02 | T-5-01 | `merchant_id` validated via regex before FS I/O | unit | `uv run pytest tests/service/test_merchants.py -x` | ❌ W0 | ⬜ pending |
| 8-02-02 | 02 | 1 | API-02 | — | server-generated id when omitted | unit | `uv run pytest tests/service/test_merchants.py::test_auto_id -x` | ❌ W0 | ⬜ pending |
| 8-03-01 | 03 | 2 | API-03 | — | structured items accepted and persisted | unit | `uv run pytest tests/service/test_sales.py::test_structured -x` | ❌ W0 | ⬜ pending |
| 8-03-02 | 03 | 2 | API-03, PARSE-01, PARSE-02 | — | Hebrew free-text parsed and persisted | unit | `uv run pytest tests/service/test_sales.py::test_hebrew_text -x` | ❌ W0 | ⬜ pending |
| 8-03-03 | 03 | 2 | API-03 | — | partial-success semantics (skipped list) | unit | `uv run pytest tests/service/test_sales.py::test_partial -x` | ❌ W0 | ⬜ pending |
| 8-04-01 | 04 | 2 | API-04, REC-04 | — | `/recommend` returns across all three tiers | integration | `uv run pytest tests/service/test_recommend.py -x` | ❌ W0 | ⬜ pending |
| 8-04-02 | 04 | 2 | API-04 | — | Tier 3 w/o model → 503 envelope | unit | `uv run pytest tests/service/test_recommend.py::test_missing_model -x` | ❌ W0 | ⬜ pending |
| 8-05-01 | 05 | 3 | — | T-5-01 | central exception handler envelope | unit | `uv run pytest tests/service/test_errors.py -x` | ❌ W0 | ⬜ pending |
| 8-05-02 | 05 | 3 | — | — | 404 on UnknownMerchantError | unit | `uv run pytest tests/service/test_errors.py::test_unknown_merchant -x` | ❌ W0 | ⬜ pending |
| 8-06-01 | 06 | 3 | INFRA-02 | — | Docker image builds with `uv sync --extra service --extra runtime` | integration | `MESHEK_DOCKER_SMOKE=1 uv run pytest tests/service/test_docker_smoke.py -x` | ❌ W0 | ⬜ pending |
| 8-06-02 | 06 | 3 | INFRA-02 | — | container `/health` responds inside `docker run` | integration | `MESHEK_DOCKER_SMOKE=1 uv run pytest tests/service/test_docker_smoke.py::test_health -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/service/__init__.py`
- [ ] `tests/service/conftest.py` — fixtures: `tmp_data_dir`, `tmp_model_path`, `client_with_model`, `client_no_model`
- [ ] `tests/service/test_health.py`
- [ ] `tests/service/test_merchants.py`
- [ ] `tests/service/test_sales.py`
- [ ] `tests/service/test_recommend.py`
- [ ] `tests/service/test_errors.py`
- [ ] `tests/service/test_docker_smoke.py` (guarded by `MESHEK_DOCKER_SMOKE` env var)
- [ ] `pyproject.toml` — add `uvicorn[standard]>=0.44` to `service` extra and new `runtime` extra with `lightgbm>=4.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Deploy to Fly.io from a clean machine | INFRA-02 | Requires external Fly.io account + secrets | `fly launch --copy-config --name meshek-ml` then `curl https://<app>.fly.dev/health` |
| Deploy to Railway (fallback) | INFRA-02 | Requires Railway account | Link repo in Railway dashboard; confirm Dockerfile detected and `/health` returns 200 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
