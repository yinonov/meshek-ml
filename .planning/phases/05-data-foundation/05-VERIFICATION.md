---
phase: 05-data-foundation
verified: 2026-04-13T00:00:00Z
status: passed
score: 11/11
requirements_met: [STOR-01, STOR-02]
overrides_applied: 0
threats:
  mitigated: [T-5-01, T-5-02, T-5-03]
  accepted: [T-5-04]
test_results:
  storage_suite: "35/35 passed"
  full_suite: "69/69 passed"
---

# Phase 5: Data Foundation — Verification Report

**Phase Goal:** Per-merchant sales history and profiles can be stored and retrieved in isolated SQLite files.
**Verified:** 2026-04-13
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

Goal-backward analysis: the delivered `meshek_ml.storage.MerchantStore` implements every observable truth required by STOR-01 and STOR-02, with filesystem isolation, canonical schema fail-fast, date dtype round-trip, upsert semantics, and layered path-traversal defense.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Merchant A and B sales persist in separate SQLite files (STOR-01 #1) | VERIFIED | `_merchant_path` builds `{root}/{merchant_id}.sqlite` (merchant_store.py:120-132). `test_filesystem_isolation` + `test_isolation_no_data_bleed` green. |
| 2 | Zero-config profile create/get (STOR-02, ROADMAP #2) | VERIFIED | `MerchantProfile` defaults `timezone='Asia/Jerusalem'`, `language='he'`, `created_at` auto-set (merchant_store.py:72-81). `test_profile_defaults_zero_config` + `test_profile_roundtrip` green. |
| 3 | Daily sales round-trip with all fields intact (STOR-01 #3, ROADMAP #3) | VERIFIED | `write_sales`/`read_sales` preserve `[date, merchant_id, product, quantity]` in canonical order; `parse_dates=["date"]` gives `datetime64[ns]`. `test_sales_roundtrip`, `test_read_sales_date_dtype`, `test_read_sales_date_range` green. |
| 4 | Canonical schema fail-fast on write (STOR-01 #4, ROADMAP #4) | VERIFIED | `write_sales` calls `validate_demand_schema(df)` (merchant_store.py:276) before INSERT; foreign merchant_id rejected (lines 278-287). 3 schema-enforcement tests green. |
| 5 | (date, product) upsert overwrites in place (D-05) | VERIFIED | `ON CONFLICT(date, product) DO UPDATE SET quantity = excluded.quantity` (merchant_store.py:306-308). `test_sales_upsert_overwrites_same_date_product` green. |
| 6 | Reopen is idempotent; migrations do not re-run destructively (D-07) | VERIFIED | `_apply_migrations` gated by `PRAGMA user_version` (merchant_store.py:169-178). `test_reopen_idempotent` green. |
| 7 | No lazy-create-on-read; unknown merchant raises loudly (D-03) | VERIFIED | `must_exist=True` branch raises `UnknownMerchantError` (merchant_store.py:202-205). `test_reader_rejects_unknown_merchant` green. |
| 8 | T-5-01 path traversal mitigated | VERIFIED | `_MERCHANT_ID_PATTERN = ^[A-Za-z0-9_-]{1,64}$` + `_merchant_path` parent-equality check. 14 hostile + 6 safe parametrized cases + defense-in-depth test green. |
| 9 | T-5-02 SQL injection mitigated | VERIFIED | All caller values flow through `?` placeholders. Only f-string SQL is `PRAGMA user_version = {int(target)}` with a hardcoded int (merchant_store.py:177). Grep audit clean. |
| 10 | T-5-03 cross-merchant data bleed mitigated | VERIFIED | `write_sales` rejects foreign `merchant_id` rows with `SchemaValidationError` (merchant_store.py:278-287); per-file isolation is the second layer. `test_write_rejects_foreign_merchant_id` + `test_isolation_no_data_bleed` green. |
| 11 | Short-lived connection lifecycle with context-manager protocol | VERIFIED | `__enter__`/`__exit__`/`close()` idempotent (merchant_store.py:217-229). Used throughout test suite without ResourceWarning. |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/meshek_ml/storage/__init__.py` | Re-exports public API | VERIFIED | Exports `MerchantStore`, `MerchantProfile`, `MerchantStoreError`, `UnknownMerchantError`, `InvalidMerchantIdError`. |
| `src/meshek_ml/storage/merchant_store.py` | `MerchantStore` + migrations + path safety, ≥180 lines | VERIFIED | 335 lines; all required constants, error hierarchy, model, helpers, migration ladder, and class methods present. |
| `tests/storage/conftest.py` | `data_root` fixture via `monkeypatch.setenv` | VERIFIED | Lines 8-14. |
| `tests/storage/test_merchant_store.py` | 9+ tests (profile CRUD, round-trip, dtype, range, upsert, reopen) | VERIFIED | 9 tests, all green. |
| `tests/storage/test_isolation.py` | Filesystem isolation + no bleed | VERIFIED | 2 tests green. |
| `tests/storage/test_schema_enforcement.py` | 3 fail-fast tests | VERIFIED | 3 tests green. |
| `tests/storage/test_path_traversal.py` | T-5-01 parametrized hostile + safe cases | VERIFIED | 21 parametrized cases green. |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `merchant_store.py` | `forecasting.schema` | `from meshek_ml.forecasting.schema import REQUIRED_COLUMNS, SchemaValidationError, validate_demand_schema` | WIRED (line 30-34) |
| `write_sales` | `validate_demand_schema` | fail-fast call before INSERT | WIRED (line 276) |
| `__init__` | filesystem | `_validate_merchant_id` + `_merchant_path` parent check | WIRED (lines 199-200) |
| `conftest` | `MESHEK_DATA_DIR` | `monkeypatch.setenv` | WIRED (line 13) |
| `_data_root()` | env var | Re-read per call (no cache) | WIRED (line 94) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Storage suite green | `pytest tests/storage/ -q` | `35 passed in 0.53s` | PASS |
| Full regression suite green | `pytest -q --no-cov` | `69 passed, 3 warnings in 5.06s` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| STOR-01 | Sales history persisted per-merchant in isolated SQLite files | SATISFIED | Truths 1, 3, 4, 5, 6; isolation + round-trip + schema-enforcement tests green |
| STOR-02 | Merchant profiles created and retrievable | SATISFIED | Truth 2; profile CRUD tests green |

No orphaned requirements: Phase 5 claimed STOR-01 and STOR-02 in both plan frontmatters; REQUIREMENTS.md maps only these two IDs to Phase 5.

### Threat Model Coverage

| Threat | Disposition | Evidence |
|--------|-------------|----------|
| T-5-01 path traversal | Mitigated | Regex whitelist + `Path.resolve()` parent-equality check; 14 hostile + 6 safe + defense-in-depth parametrized cases green |
| T-5-02 SQL injection | Mitigated | `?` placeholders throughout; `grep -nE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)'` returns empty; only f-string SQL is `PRAGMA user_version = {int(target)}` with hardcoded constant |
| T-5-03 cross-merchant leakage | Mitigated | Foreign-id guard in `write_sales` + per-file isolation; both tested |
| T-5-04 DoS via huge DataFrame | Accepted | Trusted caller (meshek app), v1.1 volumes low; documented in 05-02 plan and SUMMARY |

### Anti-Patterns Found

None that block the goal. The 05-REVIEW.md code review identified 3 warnings and 6 info items — all non-blocking:
- **WR-01** `read_sales` dtype inconsistency on empty result — future robustness fix
- **WR-02** Sales PK `(date, product)` relies on per-file isolation — latent foot-gun, not an active bug
- **WR-03** `MESHEK_DATA_DIR` default resolves against CWD silently — misconfiguration risk, not a security bug

These are tracked in 05-REVIEW.md for follow-up but do not affect STOR-01/STOR-02 goal achievement.

### Human Verification Required

None. All must-haves are verifiable programmatically via the test suite.

### Gaps Summary

None. Phase 5 fully delivers the per-merchant SQLite storage layer specified by ROADMAP success criteria 1–4, satisfies STOR-01 and STOR-02, mitigates T-5-01/02/03 with tested layered defenses, and accepts T-5-04 with documented rationale. 35/35 storage tests green; 69/69 full project suite green; no regressions.

---

*Verified: 2026-04-13*
*Verifier: Claude (gsd-verifier)*
