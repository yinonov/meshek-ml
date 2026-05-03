---
status: complete
phase: 07-hebrew-input-parsing
source: [07-SUMMARY.md]
started: 2026-04-15
updated: 2026-04-15
mode: auto-verified
---

## Current Test

[testing complete]

## Tests

### 1. Name → canonical id (PARSE-01)
expected: Hebrew product names including singular, plural, and common misspellings resolve to the correct canonical product_id against the real shipped `configs/parsing/products_he.yaml`.
result: pass
evidence: |
  parse_sales_line("20 עגבניות")  -> tomato
  parse_sales_line("עגבניה 5")    -> tomato (singular)
  parse_sales_line("עגבנייה 5")   -> tomato (misspelling alias)

### 2. Order-invariant quantity + unit (PARSE-02)
expected: Number may precede or follow the product name; kg variants (קג / ק״ג / קילו) all fold to Unit.KG.
result: pass
evidence: |
  parse_sales_line("20 עגבניות")       -> qty=20 unit=KG
  parse_sales_line("עגבניות 20 קג")    -> qty=20 unit=KG
  parse_sales_line("5 ק״ג מלפפונים")   -> cucumber qty=5 unit=KG

### 3. Structured ParseError on bad input
expected: Unrecognised / malformed input returns ParseError with a specific kind rather than silently producing a wrong product_id.
result: pass
evidence: |
  ""                -> ParseError(kind=empty_input)
  "xyzzy 5"         -> ParseError(kind=unknown_product)
  "עגבניות"         -> ParseError(kind=missing_quantity)
  "5 10 עגבניות"    -> ParseError(kind=ambiguous_quantity)

### 4. Catalog loads from shipped YAML
expected: `load_catalog(DEFAULT_CATALOG_PATH)` loads the production 30-product seed without error.
result: pass
evidence: "len(catalog.products) == 30 against configs/parsing/products_he.yaml"

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0

## Gaps

[none — all ROADMAP success criteria verified against the real shipped catalog]

## Notes

- Pure Python library phase; no UI, no server, no cold-start surface — UAT executed programmatically against the real `configs/parsing/products_he.yaml` rather than conversationally.
- `pytest tests/parsing` could not be re-executed in this session because the global venv build of `pyarrow` fails (missing `cmake` — unrelated to phase 07). Phase 07's own `07-VERIFICATION.md` already records 176/176 full-suite pass at commit `4bea413`.
