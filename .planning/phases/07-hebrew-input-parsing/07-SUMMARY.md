---
phase: 07-hebrew-input-parsing
milestone: v1.1
status: complete
completed: 2026-04-14
requirements: [PARSE-01, PARSE-02]
plans:
  - 07-01  # normalize_text + Unit enum + unit aliases
  - 07-02  # ProductCatalog + products_he.yaml seed
  - 07-03  # parse_sales_line + ParsedSale/ParseError
  - 07-04  # public API + D-18 integration gate
---

# Phase 7: Hebrew Input Parsing — Summary

**One-liner:** A pure-Python, dictionary-based Hebrew parser converts free-text merchant lines like `"20 עגבניות"` or `"עגבניות 20 קג"` into `(canonical_product_id, quantity, Unit)`, returning structured `ParseError` on any recoverable failure — ready to be called from the Phase 8 `POST /sales` route.

## Goal (from ROADMAP)

> Free-text Hebrew sales input is reliably mapped to canonical product IDs and quantities before being stored.

**Requirements closed:** PARSE-01 (name → canonical id), PARSE-02 (order-invariant quantity + unit). PARSE-03 (rapidfuzz fuzzy fallback) remains deferred to v2 by design.

## Success Criteria → Implementing Plans

| # | ROADMAP Success Criterion | Implemented by | Verified by |
|---|---------------------------|----------------|-------------|
| 1 | Hebrew product names including singular, plural, and common misspellings are resolved to the correct canonical product ID | 07-01 (normalize_text, niqqud strip, final-letter fold) + 07-02 (seed catalog with singular/plural/misspelling aliases per product) | `tests/parsing/test_integration.py::test_singular_plural_misspelling_same_id` (case a) |
| 2 | Quantity and unit extractable regardless of whether the number precedes or follows the product name | 07-03 (`parse_sales_line` greedy longest-first alias window + single numeric token regex) | `tests/parsing/test_integration.py::test_number_before_and_after_order_invariant` (case b) + `test_kg_unit_variants_all_map_to_kg` (case e) |
| 3 | Unrecognised Hebrew input returns a structured parse error rather than silently producing a wrong product ID | 07-03 (`ParseError(kind="unknown_product")`, `"empty_input"`, `"missing_quantity"`, `"ambiguous_quantity"`, `"bad_quantity"`) | `tests/parsing/test_integration.py::test_unknown_product_returns_structured_error` (case c) + `test_empty_and_whitespace` (case f) |

## Requirements → Plans Traceability

| Req | Description | Plans |
|-----|-------------|-------|
| PARSE-01 | Hebrew product name → canonical product_id | 07-01 (normalize), 07-02 (catalog+seed), 07-03 (greedy resolve), 07-04 (real-catalog gate) |
| PARSE-02 | Quantity + unit extraction, order-invariant | 07-01 (Unit enum + kg/unit/crate aliases), 07-03 (number regex + leftover unit scan), 07-04 (kg-variants gate) |

## Plan Waves

- **07-01 (Wave 1)** — `src/meshek_ml/parsing/normalize.py`: `Unit` enum, `normalize_text` (strip niqqud, fold final letters, collapse whitespace, drop punctuation), `match_unit_token` (קג / ק״ג / קילו → KG etc.). Commit `ccf449b`.
- **07-02 (Wave 2)** — `src/meshek_ml/parsing/catalog.py` + `configs/parsing/products_he.yaml`: frozen `Product`/`ProductCatalog`, duplicate-alias detection, prebuilt normalized index, 30-product seed (tomato → corn). Commits `23e4b7c`, `1a8617a` (SUMMARY `07-02-SUMMARY.md`).
- **07-03 (Wave 3)** — `src/meshek_ml/parsing/parser.py`: `ParsedSale`, `ParseError(kind=...)`, `parse_sales_line` (normalize → extract single number → greedy longest-alias window → leftover unit scan → default_unit fallback), `parse_sales_lines` batch helper. Commit `81c74af`.
- **07-04 (Wave 4)** — `src/meshek_ml/parsing/__init__.py` public API + `tests/parsing/test_integration.py` D-18 gate against real seed YAML. Commit `4bea413`.

## Verification

- `pytest tests/parsing -q --no-cov` → **56 passed** (parsing-focused suite).
- `pytest -q --no-cov` → **176 passed, 0 regressions** across all subsystems.
- Integration suite exercises the real shipped `configs/parsing/products_he.yaml` — not a test fixture — guaranteeing the catalog shipped to production actually parses merchant input correctly.

## Known Gaps

- **07-01-SUMMARY.md and 07-03-SUMMARY.md were not written** at execution time (only commits landed). All functionality is exercised by the integration suite in 07-04 and the unit suites committed alongside those plans, so coverage is complete even though the per-plan SUMMARY docs are absent. Not blocking PARSE-01 / PARSE-02 closure.
- PARSE-03 (rapidfuzz fuzzy fallback) is intentionally deferred to v2 per 07-CONTEXT §Scope.

## Downstream Enablement

Phase 8 can now:

```python
from meshek_ml.parsing import (
    parse_sales_line, load_catalog, DEFAULT_CATALOG_PATH,
    ParsedSale, ParseError, Unit,
)
```

and wire `POST /sales` to call `parse_sales_line(body.text, catalog)` with a FastAPI-lifespan-loaded `ProductCatalog`.

## Self-Check: PASSED

- FOUND: src/meshek_ml/parsing/{normalize,catalog,parser,__init__}.py
- FOUND: configs/parsing/products_he.yaml
- FOUND: tests/parsing/{test_normalize,test_catalog,test_parser,test_integration}.py
- FOUND commits: ccf449b, 23e4b7c, 81c74af, 4bea413
- VERIFIED: 176/176 full-suite pass
