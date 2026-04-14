---
phase: 07-hebrew-input-parsing
plan: 00
type: overview
requirements: [PARSE-01, PARSE-02]
---

<objective>
Phase 7 overview. Deliver a pure-Python Hebrew sales-line parser under `src/meshek_ml/parsing/` that maps free-text merchant input (e.g. `"20 עגבניות"`, `"עגבניות 20 קג"`) to `(canonical_product_id, quantity, unit)` via a YAML-backed alias catalog. No HTTP wiring, no fuzzy matching, no LLM. Phase 8 consumes this library.

Output: New package `meshek_ml.parsing` with `ProductCatalog`, `Unit`, `ParsedSale`, `ParseError`, `parse_sales_line`, `parse_sales_lines`; YAML seed catalog at `configs/parsing/products_he.yaml`; pytest suite under `tests/parsing/` covering the six required D-18 cases.
</objective>

<wave_structure>

Four sequential waves. Each wave is a single focused plan; parallelism is limited here because all plans feed one pipeline (normalize → catalog → parser → package-level integration).

| Wave | Plan | Focus | Depends on |
|------|------|-------|------------|
| 1 | 07-01 | `normalize.py` — niqqud stripping, final-letter folding, `Unit` enum, unit-token map, `normalize_text()` | — |
| 2 | 07-02 | `catalog.py` + `configs/parsing/products_he.yaml` — `ProductCatalog` dataclass, YAML loader, prebuilt alias→id dict (aliases normalized at build time) | 07-01 |
| 3 | 07-03 | `parser.py` — `ParsedSale`, `ParseError`, `parse_sales_line`, `parse_sales_lines`; greedy longest-first alias match; order-invariant quantity extraction | 07-01, 07-02 |
| 4 | 07-04 | `parsing/__init__.py` public API + `tests/parsing/` integration tests covering the six D-18 cases against the real seed catalog | 07-01, 07-02, 07-03 |

Same-wave file overlap: none (sequential).

</wave_structure>

<requirements_coverage>

| Requirement | Plan | Notes |
|-------------|------|-------|
| PARSE-01 (names → canonical id) | 07-02 (catalog), 07-03 (match), 07-04 (e2e) | Exact-match-on-normalized-alias, greedy longest-first (D-10, D-11). |
| PARSE-02 (quantity + unit, order-invariant) | 07-03 (regex extraction), 07-04 (e2e) | Order-invariant regex, `>0` guard, multi-number → ambiguous (D-12, D-13, D-14). |

</requirements_coverage>

<success_criteria_mapping>

Phase 7 ROADMAP success criteria → plan(s) that verify them:

1. **Hebrew names (singular/plural/misspellings) → canonical id** → 07-02 builds the alias table; 07-04 asserts `tomato`/`tomatos`/a common misspelling all resolve to `tomato`.
2. **Quantity+unit extracted regardless of number-first or name-first order** → 07-03 implements; 07-04 asserts both `"20 עגבניות"` and `"עגבניות 20 קג"` parse.
3. **Unrecognised Hebrew → structured ParseError, never a wrong id** → 07-03 defines `ParseError`; 07-04 asserts `unknown_product`, `empty_input`, `bad_quantity`, `ambiguous_quantity`, `missing_quantity` kinds.

</success_criteria_mapping>

<decision_coverage>

| Decision | Plan | Status |
|----------|------|--------|
| D-01 package layout | 07-01/02/03/04 | Full (split across modules) |
| D-02 public API signatures | 07-03, 07-04 | Full |
| D-03 canonical slugs | 07-02 | Full |
| D-04 YAML catalog fields | 07-02 | Full |
| D-05 immutable ProductCatalog dataclass | 07-02 | Full |
| D-06 ~30-product seed | 07-02 | Full |
| D-07 normalization pipeline | 07-01 | Full |
| D-08 ASCII digits only | 07-03 | Full |
| D-09 unit tokens → enum | 07-01 | Full |
| D-10 exact-match only | 07-03 | Full |
| D-11 greedy longest-first | 07-03 | Full |
| D-12 order-invariant regex | 07-03 | Full |
| D-13 quantity > 0 | 07-03 | Full |
| D-14 multi-number → ambiguous | 07-03 | Full |
| D-15 ParseError shape | 07-03 | Full |
| D-16 no MerchantStore changes | (all — out of scope) | Full (negative) |
| D-17 no new runtime deps | 07-01/02/03 | Full |
| D-18 test cases a–f | 07-04 | Full |

</decision_coverage>

<out_of_scope>
- Any FastAPI wiring, route handler, or ingestion endpoint (Phase 8).
- rapidfuzz / Levenshtein fuzzy matching (PARSE-03, v2).
- Multi-item single-line splitting (`"20 עגבניות, 5 מלפפונים"`).
- Hebrew numerals / gematria.
- Touching `MerchantStore` or `forecasting/schema.py`.
</out_of_scope>
