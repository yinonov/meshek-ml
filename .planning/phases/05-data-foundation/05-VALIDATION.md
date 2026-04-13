---
phase: 5
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini |
| **Quick run command** | `pytest tests/storage/ -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/storage/ -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | STOR-01 | — | N/A | unit | `pytest tests/storage/ -q` | ❌ W0 | ⬜ pending |

*Populated by planner — see PLAN.md task table for full mapping.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/storage/__init__.py` — package marker
- [ ] `tests/storage/conftest.py` — `tmp_path`-based `MESHEK_DATA_DIR` fixture
- [ ] `tests/storage/test_merchant_store.py` — stubs for STOR-01, STOR-02 success criteria
- [ ] `tests/storage/test_isolation.py` — stub for filesystem-level isolation criterion
- [ ] `tests/storage/test_schema_enforcement.py` — stub for canonical-schema fail-fast criterion
- [ ] `tests/storage/test_path_traversal.py` — stub for merchant_id whitelist threat mitigation

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
