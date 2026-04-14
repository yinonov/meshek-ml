---
phase: 7
fixed_at: 2026-04-14
review_path: .planning/phases/07-hebrew-input-parsing/07-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-04-14
**Source review:** `.planning/phases/07-hebrew-input-parsing/07-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Medium + Low)
- Fixed: 4
- Skipped: 0
- Info findings (IN-01..IN-04) intentionally deferred per fix scope.
- Final parsing suite: `pytest tests/parsing -q --no-cov` → **57 passed** (was 56; MD-02 adds `test_input_too_long`).

## Fixed Issues

### MD-01: Fragile DEFAULT_CATALOG_PATH under non-editable installs

**Files modified:** `src/meshek_ml/parsing/catalog.py`, `src/meshek_ml/parsing/data/products_he.yaml` (moved from `configs/parsing/products_he.yaml` via `git mv`)
**Commit:** `9ef35e5`
**Applied fix:** Moved the seed YAML into the package tree at `src/meshek_ml/parsing/data/products_he.yaml` so hatchling's wheel target (`packages = ["src/meshek_ml"]`) includes it automatically — no `pyproject.toml` package-data change required. `DEFAULT_CATALOG_PATH` is now computed by a private `_resolve_default_catalog_path()` helper that first tries `importlib.resources.files("meshek_ml.parsing").joinpath("data/products_he.yaml")` and falls back to the legacy `configs/parsing/products_he.yaml` repo-root path as an editable-install safety net. Integration tests continue to load the real YAML via `DEFAULT_CATALOG_PATH` and pass unchanged.

### MD-02: No length cap on untrusted merchant input

**Files modified:** `src/meshek_ml/parsing/parser.py`, `tests/parsing/test_parser.py`
**Commit:** `e3e8b12`
**Applied fix:** Added `_MAX_INPUT_CHARS = 2048` module constant and an early `_err("input_too_long", text)` return at the top of `parse_sales_line` (runs before `text.strip()` and `normalize_text`). Extended `ParseErrorKind` Literal with `"input_too_long"` and added a Hebrew hint (`"הטקסט ארוך מדי"`) to `_HINTS`. New test `test_input_too_long` feeds a >2048-char input and asserts `ParseError(kind="input_too_long")`.

### LW-01: Dead try/except ValueError around float(numbers[0])

**Files modified:** `src/meshek_ml/parsing/parser.py`
**Commit:** `e9a383f`
**Applied fix:** Removed the unreachable `try/except ValueError` block. `_NUMBER_RE` only captures `\d+(?:\.\d+)?`, so every match is a valid float literal. Kept the `quantity <= 0 → bad_quantity` guard. Added a comment explaining why the conversion is safe.

### LW-02: ProductCatalog.get() is O(n) on the default-unit hot path

**Files modified:** `src/meshek_ml/parsing/catalog.py`
**Commit:** `255a656`
**Applied fix:** Added a new frozen-dataclass field `by_id: MappingProxyType[str, Product]` on `ProductCatalog` (alongside `alias_index`). `load_catalog` builds `{p.product_id: p for p in products}` and wraps it in `MappingProxyType` before constructing the catalog. `ProductCatalog.get()` now delegates to `self.by_id.get(product_id)` — O(1) instead of O(n). Existing catalog/parser/integration tests all pass without modification, preserving the frozen-immutable contract.

## Deferred (out of scope)

Info-tier findings from the review were intentionally excluded by fix scope and remain open for future iterations:

- **IN-01** — Widen `parse_sales_lines` parameter type from `list[str]` to `Iterable[str]`.
- **IN-02** — Decide whether `_NUMBER_RE` should accept non-ASCII Unicode digits; pin behavior with a test or add `re.ASCII`.
- **IN-03** — Remove redundant `count=1` in `_NUMBER_RE.sub`.
- **IN-04** — Document silent greedy-first resolution for multi-product lines in the module docstring (possibly introduce `ambiguous_product` kind when Phase 8 bundles multi-item lines).

---

*Fixed: 2026-04-14*
*Fixer: Claude (gsd-code-fixer)*
*Iteration: 1*
