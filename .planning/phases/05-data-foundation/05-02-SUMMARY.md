---
phase: 05-data-foundation
plan: 02
subsystem: storage
tags: [tdd, wave-2, green, storage, sqlite, security]
wave: 2
requirements_completed: [STOR-01, STOR-02]
dependency_graph:
  requires:
    - 05-01 (RED tests under tests/storage/)
    - src/meshek_ml/forecasting/schema.py (REQUIRED_COLUMNS, validate_demand_schema, SchemaValidationError)
  provides:
    - meshek_ml.storage.MerchantStore — per-merchant SQLite data access API
    - meshek_ml.storage.MerchantProfile — Pydantic profile model
  affects:
    - Phase 6 RecommendationEngine (will call store.read_sales)
    - Phase 7 Hebrew parser → Phase 8 /sales endpoint (will call store.write_sales)
tech_stack:
  added: []
  patterns:
    - stdlib sqlite3 with PRAGMA user_version migration ladder
    - WAL journal_mode for short-lived per-request connections
    - Pydantic BaseModel at the boundary, raw rows in storage
    - Defense-in-depth path safety (regex whitelist + Path.resolve parent check)
    - Parameterized SQL only — zero f-string interpolation of caller values
key_files:
  created:
    - src/meshek_ml/storage/__init__.py
    - src/meshek_ml/storage/merchant_store.py
  modified: []
decisions:
  - Read MESHEK_DATA_DIR per call (no module-level cache) so monkeypatch.setenv works in tests
  - Coerce DataFrame dates to ISO date strings before INSERT; rely on parse_dates=["date"] on read for datetime64[ns] round-trip (Pitfall 1)
  - Single migration _migration_001_initial creates merchant_profile + sales tables; user_version baseline = 1
  - Idempotent close() so context-manager exits never raise even if already closed
metrics:
  tasks: 1
  files_created: 2
  lines_added: 350
  tests_green: 35
  full_suite: "69 passed"
  completed: 2026-04-13
---

# Phase 05 Plan 02: MerchantStore Implementation Summary

**One-liner:** Per-merchant SQLite storage layer (stdlib sqlite3 + Pydantic) with filesystem isolation, fail-fast schema enforcement, (date, product) upsert, and defense-in-depth path safety.

## What Was Built

A new `meshek_ml.storage` subpackage that turns every Wave 0 RED test from Plan 05-01 GREEN.

| File | Purpose |
|------|---------|
| `src/meshek_ml/storage/__init__.py` | Public re-exports: `MerchantStore`, `MerchantProfile`, `MerchantStoreError`, `UnknownMerchantError`, `InvalidMerchantIdError` |
| `src/meshek_ml/storage/merchant_store.py` | `MerchantStore` class, `MerchantProfile` model, migration ladder, path-safety helpers (334 lines) |

## Public API

```python
from meshek_ml.storage import (
    MerchantStore,
    MerchantProfile,
    MerchantStoreError,
    UnknownMerchantError,
    InvalidMerchantIdError,
)

class MerchantProfile(BaseModel):
    merchant_id: str
    name: str | None = None
    timezone: str = "Asia/Jerusalem"   # D-13
    language: str = "he"                # D-13
    created_at: str                     # ISO-8601, auto-set via Field(default_factory=...)

class MerchantStore:
    def __init__(self, merchant_id: str, *, must_exist: bool = False) -> None: ...
    def __enter__(self) -> "MerchantStore": ...
    def __exit__(self, exc_type, exc, tb) -> None: ...
    def close(self) -> None: ...                                # idempotent
    def create_profile(self, profile: MerchantProfile) -> MerchantProfile: ...
    def get_profile(self) -> MerchantProfile | None: ...
    def write_sales(self, df: pd.DataFrame) -> int: ...         # upsert; returns row count
    def read_sales(self, start=None, end=None) -> pd.DataFrame: ...  # canonical column order
```

Data root resolved on every call from `$MESHEK_DATA_DIR` (default `data/merchants/`). Each merchant lives at `{root}/{merchant_id}.sqlite`.

## Test Results

```
$ PYTHONPATH=.../src .venv/bin/python -m pytest tests/storage/ -q
35 passed in 0.68s

$ PYTHONPATH=.../src .venv/bin/python -m pytest -q --no-cov
69 passed, 3 warnings in 10.25s
```

All 35 storage tests green; full project suite (69 tests) still green. Pre-existing warnings in `forecasting/schema.py` and `gymnasium` are unchanged and out of scope.

### Acceptance Audit

| Check | Result |
|-------|--------|
| `merchant_store.py` ≥ 180 lines | 334 lines |
| `from meshek_ml.forecasting.schema import` present | yes |
| `validate_demand_schema(df)` call present | yes |
| `_MERCHANT_ID_PATTERN = re.compile` present | yes |
| `ON CONFLICT(date, product) DO UPDATE` present | yes |
| `PRAGMA user_version` present | yes (4 occurrences) |
| `parse_dates=["date"]` present | yes |
| `grep -nE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)'` | empty (T-5-02 clean) |
| Smoke check writes `/tmp/meshek-smoke/smoke.sqlite` | confirmed |

## Threat Dispositions

| Threat | Disposition | How |
|--------|-------------|-----|
| **T-5-01** Path traversal via `merchant_id` | mitigated | (1) `_MERCHANT_ID_PATTERN = ^[A-Za-z0-9_-]{1,64}$` rejects `/`, `\`, `.`, `\x00`, unicode, oversized, empty; (2) `_merchant_path` resolves and asserts `candidate.parent == _data_root()`; verified by 14 hostile + 6 safe parametrized cases |
| **T-5-02** SQL injection | mitigated | Every caller value passes through `?` placeholders. The only f-string SQL is `PRAGMA user_version = {int(target)}` where `target` is a hardcoded module constant. Audited via `grep -nE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)'` — no matches. |
| **T-5-03** Cross-merchant data bleed via `write_sales` | mitigated | `write_sales` rejects any row whose `merchant_id != self.merchant_id` with `SchemaValidationError`. Filesystem isolation (D-01) is the second layer. Verified by `test_write_rejects_foreign_merchant_id` and `test_isolation_no_data_bleed`. |
| **T-5-04** DoS via huge DataFrame | accepted | v1.1 volumes are tens of rows/day per merchant; caller is the trusted meshek app. Revisit if Phase 8 exposes `/sales` to untrusted input. |

## Requirements Coverage

| Req | Criterion | Test(s) | Status |
|-----|-----------|---------|--------|
| STOR-01 #1 | Filesystem isolation per merchant | `test_filesystem_isolation`, `test_isolation_no_data_bleed` | green |
| STOR-01 #3 | Sales round-trip with canonical columns + datetime64[ns] | `test_sales_roundtrip`, `test_read_sales_date_dtype`, `test_read_sales_date_range` | green |
| STOR-01 #4 | Fail-fast schema enforcement | `test_write_rejects_missing_columns`, `test_write_rejects_null_values`, `test_write_rejects_foreign_merchant_id` | green |
| STOR-01 (D-05) | (date, product) upsert | `test_sales_upsert_overwrites_same_date_product` | green |
| STOR-01 (D-07) | Reopen idempotent | `test_reopen_idempotent` | green |
| STOR-02 | Profile zero-config defaults | `test_profile_roundtrip`, `test_profile_defaults_zero_config`, `test_get_profile_returns_none_when_missing` | green |
| D-03 | No lazy-create-on-read | `test_reader_rejects_unknown_merchant` | green |

## Deviations from Plan

None — plan executed exactly as written. The implementation matches every concrete requirement in the `<action>` block (constants, error hierarchy, MerchantProfile defaults, helpers, migration ladder, MerchantStore methods). No CLAUDE.md adjustments needed; no auto-fixes triggered; no architectural decisions deferred to the user.

Test files under `tests/storage/` were **not** modified — verified clean.

## Hand-off Notes

**To Phase 6 (RecommendationEngine):**
> Use `with MerchantStore(merchant_id) as store: df = store.read_sales(start, end)` to load history for the recommendation engine. The returned DataFrame already has canonical column order `[date, merchant_id, product, quantity]` and `date` as `datetime64[ns]`. Catch `UnknownMerchantError` (raised when `must_exist=True`) for cold-start (Tier 1) merchants.

**To Phase 8 (FastAPI):**
> Construct one short-lived `MerchantStore` per request inside the route handler. Do not share connections across threads or requests. WAL mode is enabled, so concurrent reads on the same merchant are safe; concurrent writes serialize at the file level. Always use the context manager (`with MerchantStore(...) as store:`) so `close()` runs on exception paths.

**Data root:**
> Set `MESHEK_DATA_DIR=/var/lib/meshek/merchants` in production deployments. The default `data/merchants/` is resolved relative to CWD and is only appropriate for local development.

## Self-Check: PASSED

- [x] FOUND: `src/meshek_ml/storage/__init__.py`
- [x] FOUND: `src/meshek_ml/storage/merchant_store.py` (334 lines)
- [x] FOUND: commit `ecac0ec` (`feat(05-02): implement MerchantStore SQLite storage layer`)
- [x] 35/35 storage tests green
- [x] 69/69 full project suite green
- [x] T-5-02 audit clean (no f-string SQL with caller input)
- [x] Smoke check creates `{MESHEK_DATA_DIR}/smoke.sqlite`
- [x] tests/storage/ unchanged
