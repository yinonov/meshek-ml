---
phase: 10-fix-cloudrun-smoke-test
plan: "01"
subsystem: testing/deploy
tags: [smoke-test, cloud-run, bug-fix, api-contract]
dependency_graph:
  requires: []
  provides: [corrected-smoke-test]
  affects: [tests/deploy/test_cloudrun_smoke.py]
tech_stack:
  added: []
  patterns: [flat-path API with merchant_id in body, stdlib urllib smoke test]
key_files:
  created: []
  modified:
    - tests/deploy/test_cloudrun_smoke.py
decisions:
  - Followed plan exactly — all four bugs (import, sales path, sales assertions, recommend path) fixed in a single atomic commit
metrics:
  duration_minutes: 5
  completed_date: "2026-04-16"
  tasks_completed: 1
  tasks_total: 1
  files_changed: 1
---

# Phase 10 Plan 01: Fix Cloud Run Smoke Test Summary

**One-liner:** Fixed four bugs in Cloud Run smoke test — corrected flat API paths (`/sales`, `/recommend`), moved `merchant_id` to request body, added `date` field, and replaced `parsed` assertions with `accepted_rows`/`skipped`.

## What Was Done

The smoke test at `tests/deploy/test_cloudrun_smoke.py` was written during Phase 8.1 against a path-per-merchant API shape (`/merchants/{id}/sales`, `/merchants/{id}/recommend`) that was never implemented. The actual Phase 8 API uses flat paths with `merchant_id` in the request body. This plan fixed all mismatches so the test correctly mirrors the live Cloud Run service contract.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix smoke test paths, payloads, and assertions | c045ed7 | tests/deploy/test_cloudrun_smoke.py |

## Changes Made

**Bug 1 — Missing import:** Added `from datetime import date as _date` to the imports section.

**Bug 2 — Wrong sales path and payload:** Changed `_post(f"/merchants/{merchant_id}/sales", {"text": ...})` to `_post("/sales", {"merchant_id": merchant_id, "date": _date.today().isoformat(), "text": ...})`.

**Bug 3 — Wrong sales assertions:** Replaced assertion on `parsed` (list, non-empty) with assertions on `accepted_rows` (int >= 1) and `skipped` (list) — matching the `SalesResponse` schema.

**Bug 4 — Wrong recommend path:** Changed `_post(f"/merchants/{merchant_id}/recommend", {})` to `_post("/recommend", {"merchant_id": merchant_id})`.

Also updated the module docstring to reflect the corrected API shape.

## Verification

- `pytest tests/deploy/test_cloudrun_smoke.py --collect-only -q` exits 0, collects 1 test
- `grep -c "merchants/{merchant_id}"` returns 0 (no path-per-merchant references remain)
- `grep -c "accepted_rows"` returns 3 (assertions present)
- `grep -c "parsed"` returns 0 (old assertions removed)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — the test file contains no placeholder data. All values are derived from live API responses or runtime computation (`_date.today()`).

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries introduced. The fix only corrects the test client to match the existing API contract.

## Self-Check: PASSED

- `tests/deploy/test_cloudrun_smoke.py` — FOUND (modified, committed c045ed7)
- Commit c045ed7 — FOUND in git log
