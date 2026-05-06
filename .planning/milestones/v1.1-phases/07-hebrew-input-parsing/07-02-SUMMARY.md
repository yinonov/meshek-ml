---
phase: 07-hebrew-input-parsing
plan: 02
subsystem: parsing
tags: [catalog, yaml, hebrew, aliases]
requires:
  - 07-01  # normalize_text, Unit enum
provides:
  - ProductCatalog
  - Product
  - CatalogError
  - load_catalog
  - DEFAULT_CATALOG_PATH
affects:
  - configs/parsing/products_he.yaml
  - src/meshek_ml/parsing/catalog.py
  - tests/parsing/test_catalog.py
tech_stack:
  added: []
  patterns:
    - frozen dataclass with MappingProxyType for immutable index
    - yaml.safe_load only (T-7-03)
    - normalize-at-build-time → runtime resolve is a single dict.get
key_files:
  created:
    - configs/parsing/products_he.yaml
    - src/meshek_ml/parsing/catalog.py
    - tests/parsing/test_catalog.py
  modified: []
decisions:
  - Implicit display_he/display_en aliases are added to the index in addition to explicit aliases; duplicate detection applies uniformly.
  - max_alias_token_count is computed once at load_catalog time and stored as a field (frozen-dataclass-friendly).
  - Product.get() performs a linear scan (~30 entries); not on hot path.
metrics:
  tasks_completed: 1
  duration_minutes: 5
  completed_date: 2026-04-14
---

# Phase 7 Plan 02: Hebrew Product Catalog Summary

Frozen ProductCatalog + YAML seed of 30 staple Israeli greengrocer products with prebuilt normalized alias index for O(1) Plan-03 matching.

## What Shipped

- **`configs/parsing/products_he.yaml`** — 30 products across vegetables, fruits, herbs, spices. Each entry: ASCII slug `id`, `display_he`, `display_en`, `category`, `default_unit` (kg/gram/unit/crate), and ≥2 Hebrew aliases (singular + plural + misspelling). Includes multi-word aliases (`פלפל אדום`, `תפוח אדמה`, `תות שדה`) so `max_alias_token_count = 2` for Plan 03's greedy matcher.
- **`src/meshek_ml/parsing/catalog.py`** — `Product` and `ProductCatalog` frozen dataclasses, `CatalogError(ValueError)`, `load_catalog(path)`, and `DEFAULT_CATALOG_PATH`. Explicit aliases + implicit `display_he`/`display_en` are normalized at build time and inserted into a `MappingProxyType` alias index. Duplicate normalized aliases across different products raise `CatalogError` eagerly.
- **`tests/parsing/test_catalog.py`** — 14 tests covering seed size, Unit enum conformance, misspelling-alias floor, alias index size, singular/plural/misspelling resolve for tomato, unknown-returns-None, `get` by id, `max_alias_token_count >= 2`, implicit display_en indexing, duplicate-alias raises, invalid-unit raises, missing top-level products raises, and frozen-dataclass immutability.

## Verification

```
tests/parsing/test_catalog.py ..............  [100%]
tests/parsing/test_normalize.py ...............  [100%]
33 passed in 0.13s
```

Smoke: `load_catalog(DEFAULT_CATALOG_PATH)` → 30 products, alias index of 126 entries, `max_alias_token_count = 2`.

## Commits

- `23e4b7c` feat(07-02): add parsing.catalog with YAML seed of ~30 staple products

## Deviations from Plan

None — plan executed exactly as written.

Minor structural choices within plan latitude:
- `ProductCatalog.max_alias_token_count` is a plain dataclass field (default 0) populated by `load_catalog` rather than set via `object.__setattr__` — the plan explicitly permitted either approach.
- Added two extra defensive tests (`test_invalid_unit_raises`, `test_missing_top_level_products_raises`, `test_catalog_is_frozen`, `test_alias_index_size`, `test_implicit_display_en_indexed`) beyond the seven listed in `<behavior>` — all within the loader's documented contract.

## Threat Mitigations Applied

- **T-7-03 (Tampering):** `yaml.safe_load` only, imported at module top level. No `yaml.load`.
- **T-7-04 (Integrity):** `_register_alias` raises `CatalogError` on any duplicate normalized alias with both conflicting product ids in the message. Tested.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: configs/parsing/products_he.yaml
- FOUND: src/meshek_ml/parsing/catalog.py
- FOUND: tests/parsing/test_catalog.py
- FOUND: 23e4b7c
