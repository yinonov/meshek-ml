# Phase 7: Hebrew Input Parsing - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Mode:** Auto (autonomous workflow, --only 7)

<domain>
## Phase Boundary

Deliver a pure-Python Hebrew input parser that converts merchant free-text sales
lines (e.g., `"20 עגבניות"`, `"עגבניות 20 קג"`) into a structured record of
`(canonical_product_id, quantity, unit)` before it is written to the per-merchant
SQLite sales store (Phase 5). The parser is a library function — HTTP wiring,
batch ingestion endpoints, and any LLM-based fallback are out of scope.

Covers requirements **PARSE-01** (name → canonical product id) and **PARSE-02**
(quantity + unit extraction, order-invariant). PARSE-03 (rapidfuzz fuzzy fallback)
is explicitly deferred to v2.

</domain>

<decisions>
## Implementation Decisions

### Module Placement
- **D-01:** New package `src/meshek_ml/parsing/` with modules `catalog.py`,
  `normalize.py`, `parser.py`, plus `__init__.py` re-exporting the public API.
  Keeps Hebrew concerns isolated from forecasting/recommendation/storage.
- **D-02:** Public entrypoint: `parse_sales_line(text: str, catalog: ProductCatalog) -> ParsedSale`.
  Batch helper `parse_sales_lines(lines, catalog)` returns `list[ParsedSale | ParseError]`.

### Canonical Product Catalog
- **D-03:** Canonical product IDs are lowercase ASCII slugs (e.g., `tomato`,
  `cucumber`, `bell_pepper`). These become the `product` column value in the
  existing sales schema (`forecasting/schema.py` already uses a free `product`
  string — Phase 7 tightens it to slugs without changing the column).
- **D-04:** Catalog lives in a new YAML file `configs/parsing/products_he.yaml`.
  Each entry: canonical id, display name (Hebrew + English), category, default
  unit, and a list of Hebrew aliases covering singular, plural, and the 2–3
  most common misspellings per product.
- **D-05:** Catalog is loaded once into an immutable `ProductCatalog` dataclass
  with pre-built alias → id lookup dict. No I/O in the hot path.
- **D-06:** Seed catalog covers ~30 staple greengrocer products (tomato,
  cucumber, pepper, onion, potato, carrot, lettuce, parsley, coriander, mint,
  lemon, orange, banana, apple, watermelon, melon, grape, eggplant, zucchini,
  cabbage, cauliflower, garlic, ginger, radish, beet, sweet potato, avocado,
  strawberry, mushroom, corn). Exact final list negotiated during plan phase.

### Normalization Rules
- **D-07:** Before alias lookup, apply in order: strip whitespace, remove
  Hebrew niqqud (Unicode combining marks U+0591–U+05C7), fold final letters
  (ך→כ, ם→מ, ן→נ, ף→פ, ץ→צ), lowercase Latin chars, collapse internal spaces.
- **D-08:** Numbers: accept ASCII digits `0-9` only in v1. Hebrew numerals /
  gematria are out of scope; decimals use `.` (not `,`).
- **D-09:** Units: recognize `"קג"`, `"ק״ג"`, `"קילו"`, `"גרם"`, `"יחידה"`,
  `"יחידות"`, `"ארגז"`, `"ארגזים"`. Map to a small `Unit` enum (`KG`, `GRAM`,
  `UNIT`, `CRATE`). Missing unit defaults to the product's `default_unit` from
  the catalog.

### Matching Strategy (PARSE-01)
- **D-10:** Exact-match-on-normalized-alias only. No Levenshtein/rapidfuzz in
  v1 — PARSE-03 explicitly defers that. An unrecognized token returns a
  structured `ParseError`, never a guess.
- **D-11:** Tokenization walks the normalized line and tries alias matches
  greedily longest-first (so `"פלפל אדום"` beats `"פלפל"` when both exist).

### Quantity Extraction (PARSE-02)
- **D-12:** Order-invariant regex: one pass finds a numeric token, another
  pass finds the product alias; remaining tokens are candidate unit. Covers
  both `"20 עגבניות"` and `"עגבניות 20 קג"`.
- **D-13:** Quantity must be `> 0`. Zero/negative → `ParseError(kind="bad_quantity")`.
- **D-14:** Multiple numbers in one line → `ParseError(kind="ambiguous_quantity")`.
  Callers can split the line before calling; line-splitting is not this phase's job.

### Error Shape
- **D-15:** `ParseError` is a frozen dataclass with fields:
  `kind` (str enum: `unknown_product`, `missing_quantity`, `bad_quantity`,
  `ambiguous_quantity`, `empty_input`), `raw_text` (original line), `hint`
  (optional str, human-readable Hebrew message). Return it from `parse_sales_line`
  — never raise for bad input. Unexpected bugs may still raise.

### Integration Surface
- **D-16:** This phase does NOT modify `MerchantStore`. It exposes pure
  functions. Phase 8 (API) will call `parse_sales_line` then pass the
  resolved `(product_id, quantity)` to `MerchantStore.add_sale`.
- **D-17:** No new runtime dependencies. Stdlib `re`, `unicodedata`, `yaml`
  (already in project) only. Keep the parser importable without FastAPI.

### Testing Contract
- **D-18:** Tests live under `tests/parsing/`. Required cases:
  (a) singular/plural/misspelling → same canonical id,
  (b) number before name and number after name both parse,
  (c) unrecognized product → `ParseError(kind="unknown_product")`,
  (d) niqqud-stripped input parses identically to clean input,
  (e) unit variants `"קג"` vs `"ק״ג"` vs `"קילו"` all map to `Unit.KG`,
  (f) empty/whitespace input → `ParseError(kind="empty_input")`.

</decisions>

<code_context>
## Existing Code Insights

- `src/meshek_ml/forecasting/schema.py` — `REQUIRED_COLUMNS = ["date",
  "merchant_id", "product", "quantity"]`. `product` is currently a free string;
  Phase 7 introduces canonical slugs but the column itself doesn't change.
- `src/meshek_ml/storage/merchant_store.py` — already inserts `(date,
  merchant_id, product, quantity)`. Parser output feeds this unchanged.
- `configs/` — top-level config dir already exists with sub-dirs per concern
  (`forecasting/`, `recommendation/`, etc.). Phase 7 adds `configs/parsing/`.
- No existing Hebrew handling anywhere in the repo — this is a greenfield
  package.
- Project is Python-only, no LLM call paths; PROJECT.md Out of Scope explicitly
  lists "LLM-based Hebrew parsing". D-10 respects that.

</code_context>

<specifics>
## Specific Ideas

- Keep the catalog in YAML so a non-dev can add a product alias without
  touching Python.
- Niqqud stripping is the single biggest correctness win for real merchant
  input — it must run before any lookup.
- The ~30-product catalog is a first pass. Expansion is a data edit, not a
  code change.

</specifics>

<deferred>
## Deferred Ideas

- **PARSE-03:** rapidfuzz fuzzy fallback for misspellings not in the alias list.
  Already tracked as v2 in REQUIREMENTS.md.
- Multi-line / multi-item parsing on a single input string (e.g.,
  `"20 עגבניות, 5 קג מלפפונים"`) — caller splits lines; revisit if Phase 8
  shows it's painful.
- Hebrew numeral / gematria support.
- LLM-assisted normalization — explicitly ruled out by PROJECT.md.

</deferred>
