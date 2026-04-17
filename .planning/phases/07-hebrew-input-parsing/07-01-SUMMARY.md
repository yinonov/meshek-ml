---
phase: 07-hebrew-input-parsing
plan: 01
subsystem: parsing
tags: [normalization, unicode, hebrew, units]
requires: []
provides:
  - Unit
  - normalize_text
  - match_unit_token
  - UNIT_ALIASES
affects:
  - src/meshek_ml/parsing/__init__.py
  - src/meshek_ml/parsing/normalize.py
  - tests/parsing/__init__.py
  - tests/parsing/test_normalize.py
tech_stack:
  added: []
  patterns:
    - unicodedata NFD decomposition for niqqud stripping
    - str.maketrans for final-letter fold
    - module-level alias dict built with normalized keys
key_files:
  created:
    - src/meshek_ml/parsing/__init__.py
    - src/meshek_ml/parsing/normalize.py
    - tests/parsing/__init__.py
    - tests/parsing/test_normalize.py
  modified: []
decisions:
  - Niqqud stripping uses NFD decomposition + codepoint range filter (U+0591..U+05C7) rather than a character whitelist.
  - UNIT_ALIASES dict is built at module load time with all keys already normalized, so callers do a single dict.get().
metrics:
  tasks_completed: 1
  completed_date: 2026-04-14
---

# Phase 7 Plan 01: Hebrew Normalization Primitives Summary

Pure-stdlib normalization utilities — `Unit` enum, `UNIT_ALIASES` dict, `normalize_text()`, and `match_unit_token()` — that underpin the entire parsing pipeline.

## What Shipped

- **`src/meshek_ml/parsing/__init__.py`** — Package marker (public API wired later in Plan 04).
- **`src/meshek_ml/parsing/normalize.py`** — Full D-07 normalization pipeline: niqqud stripping via `unicodedata.normalize("NFD")` + combining-mark filter, final-letter folding (`ך→כ`, `ם→מ`, `ן→נ`, `ף→פ`, `ץ→צ`) via `str.maketrans`, Latin lowercase, whitespace collapse. `Unit(str, Enum)` with four members (KG, GRAM, UNIT, CRATE). `UNIT_ALIASES` maps all D-09 Hebrew tokens (normalized at module load) to their `Unit`. `match_unit_token()` is a thin `dict.get`.
- **`tests/parsing/__init__.py`** — Empty package marker.
- **`tests/parsing/test_normalize.py`** — 19 tests covering every D-07 normalization rule (niqqud strip, final-letter fold, Latin lowercase, whitespace collapse, idempotency) and every D-09 unit alias (KG variants, GRAM, UNIT singular/plural, CRATE singular/plural, unknown returns None).

## Verification

```
tests/parsing/test_normalize.py ...................  [100%]
19 passed in 0.04s
```

Smoke: `normalize_text("עֲגָבְנִיָּה") == normalize_text("עגבניה")` — niqqud stripped. `match_unit_token(normalize_text("קילו")) is Unit.KG` — alias resolved.

## Commits

- `ccf449b` feat(07-01): add Hebrew normalization and Unit enum

## Deviations from Plan

None — plan executed as written.

## Threat Mitigations Applied

- **T-7-01 (DoS):** Only linear stdlib operations — `unicodedata.normalize`, `str.translate`, single non-backtracking `re.sub(r"\s+", " ", x)`.
- **T-7-02 (Tampering):** `Unit` enum and `UNIT_ALIASES` are module-level constants, not caller-controlled.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: src/meshek_ml/parsing/__init__.py
- FOUND: src/meshek_ml/parsing/normalize.py
- FOUND: tests/parsing/__init__.py
- FOUND: tests/parsing/test_normalize.py
- FOUND: ccf449b
