---
phase: 07-hebrew-input-parsing
security_audit: true
asvs_level: 1
audited: 2026-04-15
status: SECURED
threats_closed: 7
threats_total: 7
---

# Phase 7 Security Audit — Hebrew Input Parsing

**ASVS Level:** 1
**block_on:** critical
**Result:** SECURED — all mitigate threats verified closed; all accept threats recorded.

---

## Threat Verification

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-7-01 | Denial of Service | mitigate | `normalize.py` uses only `unicodedata.normalize` (NFD), `str.translate`, and a single precompiled `re.compile(r"\s+")` sub — all linear, no backtracking. Lines 15, 31–45, 65–77. |
| T-7-02 | Tampering | accept | Module-level `Unit(str, Enum)` constants; not caller-controlled. Accepted per threat register. |
| T-7-03 | Tampering | mitigate | `catalog.py:139` — `yaml.safe_load(text)` only. No `yaml.load` call present anywhere in `catalog.py`. |
| T-7-04 | Integrity | mitigate | `catalog.py:109–125` — `_register_alias` raises `CatalogError(f"Duplicate alias {norm!r}: {existing} vs {product_id}")` on any conflict. `test_catalog.py:103` asserts `pytest.raises(CatalogError, match="Duplicate alias")`. Both implementation and test confirmed. |
| T-7-05 | Information Disclosure | accept | Catalog content (product names) is non-sensitive. Accepted per threat register. |
| T-7-06 | Denial of Service | mitigate | `parser.py:153` — `max_window = max(1, min(catalog.max_alias_token_count, len(tokens)))`. Window bounded by `max_alias_token_count` (2 in the shipped seed). O(n·k) walk with k ≤ 5 per plan design. |
| T-7-07 | Injection | mitigate | `parser.py:68` — `_NUMBER_RE = re.compile(r"(?<!\S)(\d+(?:\.\d+)?)(?!\S)")`. Fixed-width lookbehind/lookahead, no alternation or repetition nesting; no backtracking possible. |
| T-7-08 | Information Disclosure | accept | `ParseError.raw_text` echoes caller's own string. Caller already owns it; no secrets flow through this code path. Accepted per threat register. |
| T-7-09 | Tampering | mitigate | `parser.py:161–172` — `catalog.resolve(candidate)` is the sole match gate; on miss the function falls through to `return _err("unknown_product", text)`. No guessing, no default product id, exact-on-normalized-alias only. |
| T-7-10 | Tampering | mitigate | `test_integration.py:26–31` — module-scoped fixture calls `catalog.get("tomato")` and issues `pytest.fail(...)` if absent. Any catalog edit removing tomato fails the suite before a wrong id could slip through. |
| T-7-11 | Repudiation | accept | `ParseError.raw_text` preserved on every failure return. Phase 8 logging is deferred by design. Accepted per threat register. |

---

## Accepted Risks Log

| Threat ID | Category | Rationale |
|-----------|----------|-----------|
| T-7-02 | Tampering — Unit enum values | `Unit` members are Python module-level constants set at import time; no caller path can modify them. |
| T-7-05 | Information Disclosure — Catalog content | Product display names (e.g. "tomato", "עגבנייה") are not sensitive business data. |
| T-7-08 | Information Disclosure — ParseError.raw_text | The caller supplied the text; echoing it in an error struct adds no new disclosure. |
| T-7-11 | Repudiation — ParseError lacks provenance | raw_text is preserved for future logging. Full audit trail deferred to Phase 8 per plan scope. |

---

## Unregistered Flags

None. The `## Threat Flags` section in `07-SUMMARY.md` contains no unregistered attack-surface entries. The `input_too_long` guard (`_MAX_INPUT_CHARS = 2048`, `parser.py:63,119`) is an implementation-time hardening addition; it strengthens T-7-01 and does not introduce new unregistered surface.

---

## Files Audited

- `src/meshek_ml/parsing/normalize.py`
- `src/meshek_ml/parsing/catalog.py`
- `src/meshek_ml/parsing/parser.py`
- `src/meshek_ml/parsing/__init__.py`
- `tests/parsing/test_catalog.py`
- `tests/parsing/test_integration.py`
