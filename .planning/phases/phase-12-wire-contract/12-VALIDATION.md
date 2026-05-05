---
phase: 12
slug: wire-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-05
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` → `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/recommendation/ tests/service/test_recommend.py -x --tb=short` |
| **Full suite command** | `pytest tests/ -x --tb=short` |
| **Estimated runtime** | ~30 seconds (quick), ~120 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | WIRE-01, WIRE-04 | — | Pydantic validation tightened (min_length=1, band ordering) | unit | `pytest tests/recommendation/test_schema.py -x` | ✅ existing — update inline | ⬜ pending |
| 12-01-02 | 01 | 1 | WIRE-01..WIRE-04 | — | N/A | unit | `pytest tests/recommendation/test_tier_1.py tests/recommendation/test_tier_2.py tests/recommendation/test_tier_3.py -x` | ✅ existing — update inline | ⬜ pending |
| 12-01-03 | 01 | 1 | WIRE-05 | — | Newsvendor decoupled from response path | unit | `pytest tests/recommendation/test_tier_3.py -x` | ✅ existing — update inline | ⬜ pending |
| 12-01-04 | 01 | 1 | WIRE-02, WIRE-03 | — | per-line tier/confidence migration | unit | `pytest tests/recommendation/test_engine.py -x` | ✅ existing — update inline | ⬜ pending |
| 12-02-01 | 02 | 2 | WIRE-02, WIRE-03 | — | HTTP contract per-line | integration | `pytest tests/service/test_recommend.py -x` | ✅ existing — update inline | ⬜ pending |
| 12-02-02 | 02 | 2 | WIRE-06 | — | OpenAPI reflects new shape; quantity absent | schema | `pytest tests/service/test_recommend.py::test_openapi_wire_contract -x` | ❌ W0 — new test function | ⬜ pending |
| 12-02-03 | 02 | 2 | WIRE-01..WIRE-04 | — | Full Tier-1 contract pinned | integration | `pytest tests/service/test_recommend.py::test_tier1_contract_key_set -x` | ❌ W0 — new test function | ⬜ pending |
| 12-02-04 | 02 | 2 | — | — | SERVICE_VERSION bumped to 1.2.0 | unit | `pytest tests/service/ -k version -x` (or grep assertion) | ✅ existing OR ❌ W0 if missing | ⬜ pending |
| 12-03-01 | 03 | 3 | WIRE-07 | — | meshek/ml-client types updated; PR draft opened | manual | (cross-repo PR review) | external | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/service/test_recommend.py::test_openapi_wire_contract` — new function asserting OpenAPI shape (WIRE-06)
- [ ] `tests/service/test_recommend.py::test_tier1_contract_key_set` — new contract test pinning the full key set + types (covers WIRE-01..WIRE-04)
- [ ] Inline migration of all `body["reasoning_tier"]` / `resp.reasoning_tier` / `body["confidence_score"]` / `resp.confidence_score` / `rec.quantity` references across:
  - `tests/recommendation/test_engine.py`
  - `tests/recommendation/test_tier_1.py`
  - `tests/recommendation/test_tier_2.py`
  - `tests/recommendation/test_tier_3.py`
  - `tests/recommendation/test_schema.py` (full rewrite of `_valid_response_kwargs`)
  - `tests/service/test_recommend.py`

*Existing infrastructure (pytest, app_client, no_model_client, data_dir, merchant_store_factory) covers all framework needs — no new fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `@meshek/ml-client` TypeScript types lands in meshek repo before meshek-ml PR merges | WIRE-07 | Cross-repo coordination — the PR lives in a separate git repo | 1. Open meshek PR (draft) updating `packages/types/src/recommendation.ts`, `packages/ml-client/src/guards.ts`, `packages/ml-client/src/guards.test.ts`. 2. Get both PRs reviewed. 3. Merge meshek PR first, then meshek-ml. 4. Document both URLs in `12-SUMMARY.md`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
