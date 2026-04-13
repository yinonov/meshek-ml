---
phase: "05"
phase_name: data-foundation
reviewed: 2026-04-13
depth: standard
files_reviewed: 8
status: clean
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
---

# Phase 5: Code Review Report (Post-Fix Re-Review)

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 8

## Summary

Re-review after WR-01/WR-02/WR-03 fix cycle. The storage layer is well-designed and the prior fix cycle addressed all substantive issues. Security posture is strong: parameterized SQL throughout, regex whitelist + `Path.resolve()` parent check defense-in-depth for path traversal, cross-merchant guard on writes, fail-fast on unset `MESHEK_DATA_DIR`, WAL mode, and explicit schema versioning via `PRAGMA user_version`. Tests cover isolation, path traversal (14 bad inputs), schema enforcement, upsert semantics, date dtype round-trip, and reopen idempotency.

No bugs, security issues, or warnings found. Two minor info-level observations.

## Info

### IN-01: `merchant_id` column is redundant in per-file store

**File:** `src/meshek_ml/storage/merchant_store.py:166-172`
Each SQLite file already belongs to exactly one merchant (filesystem-level isolation, D-01), so the `sales.merchant_id` column and the `merchant_id = ?` WHERE clause in `read_sales` (line 330) are structurally redundant. The cross-merchant guard in `write_sales` (lines 291-299) exists only to defend this redundancy. Dropping the column would simplify the schema, shrink storage, and remove an entire class of potential bugs. Keeping it is defensible for future multi-tenant consolidation, but that trade-off is worth documenting.

**Fix:** Either (a) add a short comment at the `sales` CREATE TABLE explaining why the column is retained despite per-file isolation, or (b) plan a future migration that drops it and relies solely on the filename for merchant scope.

### IN-02: `assert self._conn is not None` used for runtime invariant

**File:** `src/meshek_ml/storage/merchant_store.py:251, 268, 313, 346`
`assert` statements are stripped when Python runs with `-O`. Using them as runtime guards against use-after-close means a closed-store misuse would surface as a confusing `AttributeError` under `-O` instead of a clear error. Low practical risk (these are type-narrowing hints for mypy), but a typed raise is more robust.

**Fix:** Replace with an explicit check:
```python
if self._conn is None:
    raise MerchantStoreError("MerchantStore is closed")
```
Or extract a small `_require_conn()` helper that returns the connection and raises on `None`.

## Threat Model Coverage

| Threat | Status | Notes |
|--------|--------|-------|
| T-5-01 path traversal | ✓ Mitigated | Regex whitelist + `Path.resolve()` parent check; tests cover null byte, unicode, `..`, absolute, oversized |
| T-5-02 SQL injection | ✓ Mitigated | All caller values via `?` placeholders; only f-string SQL is `PRAGMA user_version = {int(target)}` (hardcoded cast) |
| T-5-03 cross-merchant leakage | ✓ Mitigated | Two-layer: per-file isolation + explicit foreign-id guard |
| T-5-04 concurrency | ⚠ Accepted | Documented in class docstring |

## Notes

- `tests/storage/__init__.py` is empty (expected — marker file only).
- `write_sales` builds the row list via a Python loop; fine at expected scale and out of v1 perf scope.
- `MerchantProfile.created_at` is a string rather than `datetime`; consistent with SQLite TEXT storage and intentional.
