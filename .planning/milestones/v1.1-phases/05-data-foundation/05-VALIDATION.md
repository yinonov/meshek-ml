---
phase: 5
slug: data-foundation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `pytest tests/storage/ -x -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/storage/ -x -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | STOR-01, STOR-02 | — | Test scaffolding | unit | `pytest tests/storage/ --collect-only -q` | ✅ | ✅ green |
| 5-01-02 | 01 | 1 | STOR-01, STOR-02 | — | Round-trip + isolation + schema tests | unit | `pytest tests/storage/ -x -q` | ✅ | ✅ green |
| 5-01-03 | 01 | 1 | STOR-01 | T-5-01 | merchant_id whitelist regex `^[A-Za-z0-9_-]{1,64}$` + Path.resolve parent check | unit | `pytest tests/storage/test_path_traversal.py -x -q` | ✅ | ✅ green |
| 5-02-01 | 02 | 2 | STOR-01, STOR-02 | T-5-01, T-5-02, T-5-03 | Parameterized SQL only; whitelist regex; cross-tenant guard | unit+integration | `pytest tests/storage/ -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/storage/__init__.py` — package marker (Plan 01 Task 1)
- [x] `tests/storage/conftest.py` — `tmp_path`-based `MESHEK_DATA_DIR` fixture (Plan 01 Task 1)
- [x] `tests/storage/test_merchant_store.py` — STOR-01, STOR-02 round-trip + profile CRUD (Plan 01 Task 2)
- [x] `tests/storage/test_isolation.py` — filesystem-level isolation between merchants (Plan 01 Task 2)
- [x] `tests/storage/test_schema_enforcement.py` — canonical-schema fail-fast on write (Plan 01 Task 2)
- [x] `tests/storage/test_path_traversal.py` — T-5-01 hostile/safe parametrized IDs (Plan 01 Task 3)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (4/4 tasks have automated commands)
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-13

---

## Validation Audit 2026-04-13

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Audit ran `pytest tests/storage/ -q` → **35 passed in 0.92s**. All 4 task entries transitioned from ⬜ pending → ✅ green. No missing tests, no manual-only escalations. Phase 5 remains Nyquist-compliant.
