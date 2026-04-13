---
phase: "05"
fixed_at: 2026-04-13
review_path: .planning/phases/05-data-foundation/05-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 5: Code Review Fix Report

**Fixed at:** 2026-04-13
**Source review:** `.planning/phases/05-data-foundation/05-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (Critical + Warning)
- Fixed: 3
- Skipped: 0

All three Warning findings were fixed. No Critical findings existed. Info findings were out of scope for this iteration.

The full storage test suite (`tests/storage/`, 35 tests) was run after WR-03 and all tests passed.

## Fixed Issues

### WR-01: `read_sales` dtype inconsistency on empty result

**Files modified:** `src/meshek_ml/storage/merchant_store.py`
**Commit:** 4fd4416
**Applied fix:** Added explicit `pd.to_datetime` coercion after `pd.read_sql_query` when `out["date"].dtype != "datetime64[ns]"`, ensuring empty result sets still yield the correct datetime64[ns] dtype. Inline comment references WR-01 for traceability.

### WR-02: Upsert schema leaves latent cross-merchant foot-gun

**Files modified:** `src/meshek_ml/storage/merchant_store.py`
**Commit:** 06564f6
**Applied fix:** Dropped the redundant `merchant_id = excluded.merchant_id` clause from the `ON CONFLICT(date, product) DO UPDATE SET` statement in `write_sales`. Chose the "drop the redundant SET" option from the review over tightening the PK because PK tightening requires a schema migration, and the dead SET clause was the actual misleading artifact. Cross-merchant safety continues to rely on the explicit foreign-id guard plus per-file isolation. Inline comment references WR-02.

### WR-03: `MESHEK_DATA_DIR` default resolves against CWD silently

**Files modified:** `src/meshek_ml/storage/merchant_store.py`
**Commit:** 438000b
**Applied fix:** Replaced the silent `"data/merchants"` default in `_data_root()` with a fail-fast `MerchantStoreError` when `MESHEK_DATA_DIR` is unset or whitespace. The error message directs tests to monkeypatch to `tmp_path` and deployments to point at a persistent volume. The existing `tests/storage/conftest.py` already sets the env var via `monkeypatch.setenv`, so the full 35-test storage suite still passes.

---

_Fixed: 2026-04-13_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
