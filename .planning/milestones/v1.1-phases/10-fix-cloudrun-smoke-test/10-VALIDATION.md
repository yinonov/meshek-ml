---
phase: 10
slug: fix-cloudrun-smoke-test
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=7.4 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` |
| **Full suite command** | `MESHEK_CLOUDRUN_SMOKE=1 MESHEK_CLOUDRUN_URL="<url>" uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` |
| **Estimated runtime** | ~5 seconds (skip mode) / ~15 seconds (live mode) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` (confirms no syntax errors; skips without env vars)
- **After every plan wave:** Run full suite with live Cloud Run URL
- **Before `/gsd-verify-work`:** Full suite must be green against live service
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | INFRA-03 | — | N/A | integration | `uv run pytest tests/deploy/test_cloudrun_smoke.py -x -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. `tests/deploy/test_cloudrun_smoke.py` already exists — this phase edits it.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Cloud Run smoke test passes | INFRA-03 | Requires live Cloud Run URL and env vars | Set `MESHEK_CLOUDRUN_SMOKE=1` and `MESHEK_CLOUDRUN_URL` to live URL, run full suite |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
