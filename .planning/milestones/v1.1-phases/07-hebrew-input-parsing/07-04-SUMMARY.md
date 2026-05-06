---
phase: 07-hebrew-input-parsing
plan: 04
subsystem: parsing
tags: [public-api, integration-tests, hebrew, d-18]
requires:
  - 07-01  # normalize_text, Unit enum
  - 07-02  # ProductCatalog, load_catalog, DEFAULT_CATALOG_PATH
  - 07-03  # parse_sales_line, ParsedSale, ParseError
provides:
  - meshek_ml.parsing public API (single import surface)
  - D-18 integration coverage against real seed catalog
affects:
  - src/meshek_ml/parsing/__init__.py
  - tests/parsing/test_integration.py
tech_stack:
  added: []
  patterns:
    - package __init__.py as the single public re-export surface
    - module-scoped pytest fixture with fail-fast drift guard on seed anchor
key_files:
  created:
    - tests/parsing/test_integration.py
  modified:
    - src/meshek_ml/parsing/__init__.py
decisions:
  - Anchor D-18 identity tests on `tomato` since its seed aliases cover
    singular (עגבנייה), common misspelling (עגבניה), and plural (עגבניות).
  - Fixture fails fast if `catalog.get("tomato") is None` so future seed
    edits that remove tomato cannot silently break the suite (T-7-10).
  - Niqqud parity test embeds `עֲגָבְנִיָּה` inline as a UTF-8 literal.
metrics:
  duration: 6m
  completed: 2026-04-14
requirements: [PARSE-01, PARSE-02]
---

# Phase 7 Plan 04: Public API + D-18 Integration Tests Summary

**One-liner:** Wire `meshek_ml.parsing` as a single-import public surface and verify all six D-18 cases end-to-end against the real shipped seed catalog, closing PARSE-01 and PARSE-02.

## What Changed

- Replaced the Plan 01 package stub `src/meshek_ml/parsing/__init__.py` with explicit re-exports of `Unit`, `normalize_text`, `Product`, `ProductCatalog`, `CatalogError`, `load_catalog`, `DEFAULT_CATALOG_PATH`, `ParsedSale`, `ParseError`, `parse_sales_line`, `parse_sales_lines`, and set `__all__`.
- Added `tests/parsing/test_integration.py` — 7 tests, one per D-18 case plus a public-API import assertion.

## D-18 Coverage

| Case | Test | Covers |
|------|------|--------|
| (a) | `test_singular_plural_misspelling_same_id` | עגבנייה / עגבניה / עגבניות → `tomato` |
| (b) | `test_number_before_and_after_order_invariant` | `"20 עגבניות"` and `"עגבניות 20 קג"` both → tomato, qty=20 |
| (c) | `test_unknown_product_returns_structured_error` | `"5 זנב"` → `ParseError(kind="unknown_product")` |
| (d) | `test_niqqud_input_parses_identically` | `עֲגָבְנִיָּה` ≡ `עגבניה` |
| (e) | `test_kg_unit_variants_all_map_to_kg` | `קג` / `ק״ג` / `קילו` → `Unit.KG` |
| (f) | `test_empty_and_whitespace` | `""` / `"   "` → `ParseError(kind="empty_input")` |
| +   | `test_public_api_importable` | all symbols reachable from `meshek_ml.parsing` root |

## Verification

- `pytest tests/parsing -q --no-cov` → **56 passed** (7 new + 49 existing across normalize/catalog/parser).
- `pytest -q --no-cov` → **176 passed, 0 regressions** across forecasting, storage, recommendation, optimization, parsing, service.
- Smoke: `parse_sales_lines(['20 עגבניות','עגבניות 20 קג','','10 זנב'], c)` → `[ParsedSale, ParsedSale, ParseError, ParseError]`.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: src/meshek_ml/parsing/__init__.py (12 exports in `__all__`)
- FOUND: tests/parsing/test_integration.py (7 tests)
- FOUND commit: 4bea413 `feat(07-04): wire Hebrew parsing public API and integration tests`
