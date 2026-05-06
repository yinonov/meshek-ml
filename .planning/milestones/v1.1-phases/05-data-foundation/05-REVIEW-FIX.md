---
phase: "05"
fixed_at: 2026-04-13
review_path: .planning/phases/05-data-foundation/05-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-04-13
**Source review:** `.planning/phases/05-data-foundation/05-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 2 (Info findings included via `--all` flag; review status was `clean`)
- Fixed: 2
- Skipped: 0

The source review's status was `clean` (no Critical or Warning findings). The user ran `/gsd-code-review-fix` with `--all`, bringing both Info findings into scope. Both were fixed in separate atomic commits.

## Fixed Issues

### IN-01: `merchant_id` column is redundant in per-file store

**Files modified:** `src/meshek_ml/storage/merchant_store.py`
**Commit:** c300019
**Applied fix:** Chose option (a) from the reviewer's suggestion. Added a SQL comment block immediately above the `CREATE TABLE IF NOT EXISTS sales` statement in `_migration_001_initial` documenting why `sales.merchant_id` is retained despite being structurally redundant under D-01 filesystem isolation: it keeps the on-disk row shape aligned with `forecasting.schema.REQUIRED_COLUMNS` and preserves a future multi-tenant consolidation migration path. Option (b) — a destructive schema migration dropping the column — was deferred because it would require bumping `_SCHEMA_VERSION`, writing migration 002, and updating `write_sales`/`read_sales` callers, all out of scope for an info-level observation.

### IN-02: `assert self._conn is not None` used for runtime invariant

**Files modified:** `src/meshek_ml/storage/merchant_store.py`
**Commit:** 19ba4dc
**Applied fix:** Implemented the "extract a small `_require_conn()` helper" variant from the reviewer's suggestion. Added a private `_require_conn(self) -> sqlite3.Connection` method on `MerchantStore` that raises `MerchantStoreError("MerchantStore is closed")` when `self._conn is None` and otherwise returns the live connection (narrowing `Optional[Connection]` to `Connection` for mypy without relying on assertions stripped under `python -O`). Replaced all four `assert self._conn is not None` usages (in `create_profile`, `get_profile`, `write_sales`, `read_sales`) with `conn = self._require_conn()` and updated the subsequent `self._conn` references inside those methods to use the local `conn` binding.

---

_Fixed: 2026-04-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
