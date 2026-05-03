---
phase: 5
slug: data-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-13
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| caller → meshek-ml Python API | `merchant_id` is caller-supplied (D-14) and becomes both a filename (D-01) and a SQL parameter. Entire attack surface. | merchant_id (string), profile fields, sales rows |
| meshek-ml Python API → SQLite file | Parameterized SQL only; no string interpolation of caller data into queries. | profile + sales rows (parameterized values) |
| meshek-ml Python API → filesystem | Path construction validated by regex whitelist + `Path.resolve()` parent check. | SQLite file path under `$MESHEK_DATA_DIR` |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-5-01 | Tampering / Elevation of Privilege | `MerchantStore.__init__` path construction | mitigate | Regex whitelist `^[A-Za-z0-9_-]{1,64}$` at `src/meshek_ml/storage/merchant_store.py:44`; parent-root check at `:140-143`; applied in `__init__` at `:218-219`. Tests: `tests/storage/test_path_traversal.py` (14 hostile + 6 safe IDs parametrized). | closed |
| T-5-02 | Tampering (SQL Injection) | All SQL in `MerchantStore` | mitigate | All values via `?` placeholders (`merchant_store.py:272-292, 339-368`). Only f-string SQL permitted: `PRAGMA user_version = {int}` at `:196` with hardcoded int from `_MIGRATIONS`. Audit command `grep -nE 'f"(INSERT\|SELECT\|UPDATE\|DELETE)' src/meshek_ml/storage/merchant_store.py` returns zero matches. | closed |
| T-5-03 | Information Disclosure (cross-merchant bleed) | `write_sales` foreign `merchant_id` rows | mitigate | Guard at `merchant_store.py:310-318` raises `SchemaValidationError` on any row with `merchant_id != self.merchant_id`. Filesystem isolation (D-01) is the second layer. Test: `tests/storage/test_schema_enforcement.py::test_write_rejects_foreign_merchant_id`. | closed |
| T-5-04 | Denial of Service (disk fill) | `write_sales` executemany | accept | See Accepted Risks Log R-5-01. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-5-01 | T-5-04 | v1.1 volumes are tens of rows/day per merchant. Caller is the trusted meshek app (two-repo split), not direct internet input. Re-evaluation trigger: Phase 8 FastAPI exposure of `/sales` without rate limiting. | Yinon Oved | 2026-04-13 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-13 | 4 | 4 | 0 | gsd-security-auditor |

### Audit notes (2026-04-13)
- All 3 `mitigate` threats verified in `src/meshek_ml/storage/merchant_store.py` with matching tests.
- T-5-02 grep audit ran clean — no f-string DML/DQL in storage module.
- No `## Threat Flags` sections present in 05-01/05-02 SUMMARY.md → no unregistered attack surface.
- Bonus defensive controls observed: `_require_conn` helper replaces `assert` (IN-02 fix); `MESHEK_DATA_DIR` fail-fast prevents CWD-anchored data root; `UnknownMerchantError` blocks lazy-create-on-read.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-13
