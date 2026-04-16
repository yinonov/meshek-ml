---
phase: 07
slug: hebrew-input-parsing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/parsing -q` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~0.3 seconds (parsing), ~2 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/parsing -q`
- **After every plan wave:** Run `pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | PARSE-01, PARSE-02 | T-7-01, T-7-02 | Linear-only normalization (no backtracking regex); immutable Unit enum | unit | `pytest tests/parsing/test_normalize.py -q` | ✅ | ✅ green |
| 07-02-01 | 02 | 2 | PARSE-01 | T-7-03, T-7-04, T-7-05 | yaml.safe_load only; duplicate alias raises CatalogError | unit | `pytest tests/parsing/test_catalog.py -q` | ✅ | ✅ green |
| 07-03-01 | 03 | 3 | PARSE-01, PARSE-02 | T-7-06, T-7-07, T-7-08, T-7-09 | Window capped at max_alias_token_count; anchored numeric regex; exact-match only | unit | `pytest tests/parsing/test_parser.py -q` | ✅ | ✅ green |
| 07-04-01 | 04 | 4 | PARSE-01, PARSE-02 | T-7-10, T-7-11 | Drift guard on seed catalog anchor; raw_text preserved on ParseError | integration | `pytest tests/parsing/test_integration.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No Wave 0 setup needed — pytest was already configured, and all test files were created alongside implementation.

---

## D-18 Coverage Matrix

| Case | Description | Test | Status |
|------|-------------|------|--------|
| (a) | Singular/plural/misspelling → same id | `test_singular_plural_misspelling_same_id` | ✅ |
| (b) | Number before/after order-invariant | `test_number_before_and_after_order_invariant` | ✅ |
| (c) | Unknown product → structured error | `test_unknown_product_returns_structured_error` | ✅ |
| (d) | Niqqud parity | `test_niqqud_input_parses_identically` | ✅ |
| (e) | KG unit variants | `test_kg_unit_variants_all_map_to_kg` | ✅ |
| (f) | Empty/whitespace → empty_input error | `test_empty_and_whitespace` | ✅ |

---

## ParseError Kind Coverage (D-15)

| Error Kind | Test(s) | Status |
|------------|---------|--------|
| `empty_input` | `test_empty_input`, `test_empty_and_whitespace` | ✅ |
| `unknown_product` | `test_unknown_product`, `test_unknown_product_returns_structured_error` | ✅ |
| `missing_quantity` | `test_missing_quantity` | ✅ |
| `bad_quantity` | `test_bad_quantity_zero`, `test_bad_quantity_negative` | ✅ |
| `ambiguous_quantity` | `test_ambiguous_quantity` | ✅ |

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-16
