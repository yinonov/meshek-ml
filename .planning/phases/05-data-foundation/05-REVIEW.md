---
phase: "05"
phase_name: data-foundation
reviewed: 2026-04-13
depth: standard
files_reviewed: 8
status: issues_found
findings:
  critical: 0
  warning: 3
  info: 6
  total: 9
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-13
**Depth:** standard
**Files Reviewed:** 8

## Summary

Phase 5 implements `MerchantStore`, a per-merchant SQLite wrapper with filesystem isolation, path-traversal defense, parameterized SQL, and migration-based schema evolution. The implementation is tight and the threat model is well-addressed: T-5-01 (path traversal) has layered defenses (regex whitelist + `Path.resolve()` parent check), T-5-02 (SQLi) consistently uses `?` placeholders, T-5-03 (cross-merchant leakage) is enforced via per-file isolation and an explicit foreign-merchant guard in `write_sales`.

No critical issues. Warnings are correctness/robustness items; info items are polish.

## Warnings

### WR-01: `read_sales` dtype inconsistency on empty result

**File:** `src/meshek_ml/storage/merchant_store.py:331-334`
`parse_dates=["date"]` silently no-ops on empty result sets, so `out["date"]` becomes `object` dtype when no rows match. Downstream consumers expecting `datetime64[ns]` will see inconsistent dtype.

**Fix:** Coerce explicitly post-query:
```python
out = pd.read_sql_query(query, self._conn, params=params, parse_dates=["date"])
if out["date"].dtype != "datetime64[ns]":
    out["date"] = pd.to_datetime(out["date"])
return out[REQUIRED_COLUMNS]
```

### WR-02: Upsert schema leaves latent cross-merchant foot-gun

**File:** `src/meshek_ml/storage/merchant_store.py:303-310`
PK is `(date, product)` not including `merchant_id`. Currently per-file isolation prevents collision, but if the foreign-id guard ever relaxed, two merchants writing the same `(date, product)` into the same file would clobber each other silently. The `ON CONFLICT DO UPDATE SET merchant_id = excluded.merchant_id` clause is also a no-op.

**Fix:** Tighten PK or drop the redundant SET:
```sql
PRIMARY KEY (date, merchant_id, product)
-- or
ON CONFLICT(date, product) DO UPDATE SET quantity = excluded.quantity
```

### WR-03: `MESHEK_DATA_DIR` default resolves against CWD silently

**File:** `src/meshek_ml/storage/merchant_store.py:94`
`Path("data/merchants").resolve()` anchors to process CWD at call time. Different working directories → different data roots → orphan stores. Not a security bug (parent-equality check still pins writes) but misconfiguration is silent.

**Fix:** Fail fast if unset, or anchor to a package-relative path:
```python
default = os.environ.get("MESHEK_DATA_DIR")
if default is None:
    raise MerchantStoreError("MESHEK_DATA_DIR must be set")
return Path(default).resolve()
```

## Info

### IN-01: `create_profile` leaks `sqlite3.IntegrityError` on duplicates

**File:** `src/meshek_ml/storage/merchant_store.py:233-253`
Duplicate insert raises raw `sqlite3.IntegrityError`. Wrap as typed `MerchantStoreError` subclass for API stability.

### IN-02: `_MIGRATIONS` ordering not enforced

**File:** `src/meshek_ml/storage/merchant_store.py:166-178`
Future appends out of order would cause silent skips. Add `sorted()` at module load.

### IN-03: `read_sales` missing type annotations

**File:** `src/meshek_ml/storage/merchant_store.py:313`
`start` / `end` parameters untyped while rest of module is typed. Annotate as `str | pd.Timestamp | None`.

### IN-04: `tests/storage/__init__.py` empty

**File:** `tests/storage/__init__.py:1`
Add a one-line docstring for consistency with `src/meshek_ml/storage/__init__.py`.

### IN-05: `MerchantProfile.created_at` stored as `str`, not `datetime`

**File:** `src/meshek_ml/storage/merchant_store.py:79-81`
Loses type fidelity at the Pydantic boundary; downstream timestamp comparisons will re-parse. Prefer `datetime` and let Pydantic v2 serialize.

### IN-06: T-5-04 (concurrency) limitation not surfaced at module level

**File:** `src/meshek_ml/storage/merchant_store.py` (module docstring)
Class docstring notes "not thread-safe" but module docstring does not. Add module-level note so importers see it immediately.

## Threat Model Coverage

| Threat | Status | Notes |
|--------|--------|-------|
| T-5-01 path traversal | ✓ Mitigated | Regex whitelist + `Path.resolve()` parent check; tests cover null byte, unicode, `..`, absolute, oversized |
| T-5-02 SQL injection | ✓ Mitigated | All caller values via `?` placeholders; only f-string SQL is `PRAGMA user_version = {int(target)}` (hardcoded cast) |
| T-5-03 cross-merchant leakage | ✓ Mitigated | Two-layer: per-file isolation + explicit foreign-id guard. See WR-02 for latent schema concern |
| T-5-04 concurrency | ⚠ Accepted | Documented in class docstring; surface at module level (IN-06) |
