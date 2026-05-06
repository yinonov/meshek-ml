---
phase: 07-hebrew-input-parsing
plan: 03
subsystem: parsing
tags: [parser, hebrew, matching, errors]
requires:
  - 07-01  # normalize_text, Unit, match_unit_token
  - 07-02  # ProductCatalog
provides:
  - ParsedSale
  - ParseError
  - ParseErrorKind
  - parse_sales_line
  - parse_sales_lines
affects:
  - src/meshek_ml/parsing/parser.py
  - tests/parsing/test_parser.py
tech_stack:
  added: []
  patterns:
    - greedy longest-first sliding window for alias matching
    - anchored whole-token regex for numeric extraction
    - structured error returns (never raises on bad input)
key_files:
  created:
    - src/meshek_ml/parsing/parser.py
    - tests/parsing/test_parser.py
  modified: []
decisions:
  - Negative numbers are not matched by _NUMBER_RE (no leading minus), so "-3 עגבניות" yields missing_quantity.
  - Input length capped at 2048 chars (MD-02) to prevent DoS from malformed WhatsApp payloads.
  - ParseErrorKind includes "input_too_long" beyond the original D-15 five kinds (defensive addition).
  - Leftover-token unit scan takes the first hit; if none match, catalog default_unit is used.
metrics:
  tasks_completed: 1
  completed_date: 2026-04-14
---

# Phase 7 Plan 03: Hebrew Sales Line Parser Summary

Order-invariant parser that maps free-text Hebrew sales input to `ParsedSale` or structured `ParseError`. Greedy longest-first alias matching, anchored numeric regex, five D-15 error kinds plus defensive input-length cap.

## What Shipped

- **`src/meshek_ml/parsing/parser.py`** — `ParsedSale` and `ParseError` frozen dataclasses, `parse_sales_line(text, catalog)` and batch `parse_sales_lines`. Algorithm: normalize input → extract single numeric token (anchored `_NUMBER_RE`) → greedy longest-first sliding window over `catalog.resolve` → leftover-token unit scan → fallback to `catalog.get(product_id).default_unit`. Input capped at 2048 chars. Hebrew hints on each error kind.
- **`tests/parsing/test_parser.py`** — 17 tests covering: number-before-name, number-after-name with unit, decimal quantity, default unit from catalog, greedy longest-first (multi-word alias), empty input, unknown product, missing quantity, bad quantity (zero), negative input, ambiguous quantity, never-raises guarantee, batch mixed results, and input-too-long cap.

## Verification

```
tests/parsing/test_parser.py .................  [100%]
tests/parsing (all 3 files) 50 passed in 0.15s
```

Smoke: `parse_sales_line("20 עגבניות", catalog)` → `ParsedSale(product_id="tomato", quantity=20.0, unit=Unit.KG)`. `parse_sales_line("עגבניות 20 קג", catalog)` → same result (order-invariant).

## Commits

- `81c74af` feat(07-03): add Hebrew sales line parser with structured errors
- `e3e8b12` fix(07): cap parse_sales_line input at 2048 chars (MD-02)
- `e9a383f` fix(07): drop dead try/except around float(numbers[0]) (LW-01)

## Deviations from Plan

Minor post-plan hardening:
- Added `_MAX_INPUT_CHARS = 2048` cap and `input_too_long` error kind (MD-02 from security review).
- Removed dead `try/except ValueError` around `float(numbers[0])` since `_NUMBER_RE` only captures valid float literals (LW-01 from code review).

## Threat Mitigations Applied

- **T-7-06 (DoS):** Window size capped at `catalog.max_alias_token_count` (2 in practice); linear O(n·k) scan.
- **T-7-07 (Injection):** `_NUMBER_RE` anchored to whitespace boundaries; no backtracking.
- **T-7-08 (Info Disclosure):** `ParseError.raw_text` echoes caller input; accepted — caller owns the string.
- **T-7-09 (Tampering):** Matching is exact-on-normalized-alias only; unknown tokens → `unknown_product`, never a guessed id.
- **MD-02 (DoS):** Input length cap at 2048 chars prevents multi-megabyte normalization buffers.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/meshek_ml/parsing/parser.py
- FOUND: tests/parsing/test_parser.py
- FOUND: 81c74af
- FOUND: e3e8b12
- FOUND: e9a383f
