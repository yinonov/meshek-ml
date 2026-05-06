---
phase: 05-data-foundation
plan: 01
subsystem: storage
tags: [tdd, wave-0, red-tests, storage, security]
wave: 1
requirements_completed: [STOR-01, STOR-02]
dependency_graph:
  requires: []
  provides:
    - tests/storage/ RED contract for MerchantStore
  affects:
    - Plan 05-02 (must implement meshek_ml.storage.merchant_store to turn these green)
tech_stack:
  added: []
  patterns:
    - pytest tmp_path + monkeypatch.setenv fixture isolation
    - Parametrized security fuzz-cases for path traversal (T-5-01)
key_files:
  created:
    - tests/storage/__init__.py
    - tests/storage/conftest.py
    - tests/storage/test_merchant_store.py
    - tests/storage/test_isolation.py
    - tests/storage/test_schema_enforcement.py
    - tests/storage/test_path_traversal.py
  modified: []
decisions:
  - Used tmp_path per test (not shared in-memory DB) for full isolation of MESHEK_DATA_DIR
  - Asserted datetime64[ns] dtype explicitly to catch SQLite TEXT-round-trip regressions (Pitfall 1)
metrics:
  tasks: 3
  files_created: 6
  tests_authored: 35
  completed: 2026-04-13
---

# Phase 05 Plan 01: Storage Wave 0 RED Tests Summary

**One-liner:** RED test scaffolding locking the `MerchantStore` contract (profile CRUD, sales round-trip, schema enforcement, path-traversal defense) before any production code exists.

## What Was Built

Six test files under `tests/storage/` that fail RED with `ModuleNotFoundError: meshek_ml.storage`, forming the executable specification that Plan 05-02 must satisfy.

| File | Purpose | Tests |
|------|---------|-------|
| `tests/storage/__init__.py` | Package marker | — |
| `tests/storage/conftest.py` | `data_root` fixture (monkeypatches `MESHEK_DATA_DIR` to tmp_path) + `sample_sales_df` canonical 3-row DataFrame | — |
| `tests/storage/test_merchant_store.py` | Profile CRUD, sales round-trip, datetime64[ns] dtype, date-range filter, (date, product) upsert, reopen idempotency | 9 |
| `tests/storage/test_isolation.py` | Per-merchant filesystem isolation + no data bleed | 2 |
| `tests/storage/test_schema_enforcement.py` | Fail-fast `SchemaValidationError` on missing columns, null values, foreign merchant_id | 3 |
| `tests/storage/test_path_traversal.py` | T-5-01 parametrized hostile IDs (14) + safe IDs (6) + defense-in-depth check | 21 |
| **Total** | | **35** |

## Confirmed RED State

```
$ .venv/bin/python -m pytest tests/storage/
...
============================== 35 failed in 0.34s ==============================
```

Every failure is `ModuleNotFoundError: No module named 'meshek_ml.storage'` — the correct Wave 0 state. The contract is now locked; Plan 05-02 must make all 35 tests green without changing a single assertion.

## Requirements Coverage

| Req | Criterion | Test(s) |
|-----|-----------|---------|
| STOR-01 #1 | Per-merchant filesystem isolation | `test_filesystem_isolation`, `test_isolation_no_data_bleed` |
| STOR-01 #3 | Round-trip preserves canonical columns | `test_sales_roundtrip`, `test_read_sales_date_dtype`, `test_read_sales_date_range` |
| STOR-01 #4 | Fail-fast schema enforcement | `test_write_rejects_missing_columns`, `test_write_rejects_null_values`, `test_write_rejects_foreign_merchant_id` |
| STOR-01 | Upsert on (date, product) (D-05) | `test_sales_upsert_overwrites_same_date_product` |
| STOR-01 | Reopen idempotent (D-07) | `test_reopen_idempotent` |
| STOR-02 | Profile CRUD with zero-config defaults | `test_profile_roundtrip`, `test_profile_defaults_zero_config`, `test_get_profile_returns_none_when_missing` |
| D-03 | No lazy-create-on-read | `test_reader_rejects_unknown_merchant` |
| T-5-01 | merchant_id whitelist + path-traversal defense | `test_merchant_id_whitelist_rejects_unsafe` (14 cases), `test_merchant_id_whitelist_accepts_safe` (6 cases), `test_path_traversal_does_not_create_files_outside_root` |

## Deviations from Plan

None — plan executed exactly as written. Test bodies match the plan's `<action>` blocks verbatim.

## Hand-off Note to Plan 05-02

> Implement `src/meshek_ml/storage/merchant_store.py` against the contract encoded in `tests/storage/`. All 35 tests must turn green. Required public surface:
> - `REQUIRED_COLUMNS` (re-exported from `forecasting.schema`)
> - Exceptions: `MerchantStoreError`, `UnknownMerchantError`, `InvalidMerchantIdError`
> - `MerchantProfile` Pydantic model with fields `merchant_id`, `name`, `timezone='Asia/Jerusalem'`, `language='he'`, `created_at` (auto-set ISO-8601)
> - `MerchantStore(merchant_id, *, must_exist=False)` with context-manager protocol, `close()`, `create_profile`, `get_profile`, `write_sales(df) -> int`, `read_sales(start=None, end=None) -> pd.DataFrame`, and a public `merchant_id` attribute
> - Root directory sourced from `MESHEK_DATA_DIR` env var
> - `_validate_merchant_id` = regex `^[A-Za-z0-9_-]{1,64}$` **plus** `Path.resolve()` parent check (defense in depth)
> - Schema validation via `forecasting.schema.validate_demand_schema` + foreign-merchant_id guard
> - SQL: `?` placeholders only (T-5-02). SQLite upsert on `(date, product)` via `INSERT ... ON CONFLICT DO UPDATE`.

## Self-Check: PASSED

- [x] `tests/storage/__init__.py` FOUND
- [x] `tests/storage/conftest.py` FOUND
- [x] `tests/storage/test_merchant_store.py` FOUND (9 test functions)
- [x] `tests/storage/test_isolation.py` FOUND (2 test functions)
- [x] `tests/storage/test_schema_enforcement.py` FOUND (3 test functions)
- [x] `tests/storage/test_path_traversal.py` FOUND (21 parametrized cases)
- [x] Commit 477a28b FOUND (Task 1: conftest)
- [x] Commit cf7efbb FOUND (Task 2: merchant_store/isolation/schema tests)
- [x] Commit 5b1cb39 FOUND (Task 3: path traversal)
- [x] 35 tests fail RED with `ModuleNotFoundError: meshek_ml.storage` (correct Wave 0 state)
