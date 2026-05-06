---
status: findings
phase: 7
reviewed: 2026-04-14
depth: standard
findings_count: 8
blockers: 0
high: 0
medium: 2
low: 2
info: 4
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-14
**Depth:** standard
**Files reviewed:** 9 (4 source, 1 config, 4 tests)
**Status:** `findings` — 2 medium, 2 low, 4 info. No blockers or highs.

## Summary

Phase 7's Hebrew parser is well-structured. `yaml.safe_load` is used correctly, the numeric regex is anchored with lookarounds and has no nested quantifiers (safe from ReDoS), `normalize_text` is idempotent and pure-stdlib, and the catalog is frozen/immutable with eager duplicate-alias detection. Tests cover the D-18 closure gate thoroughly.

Two medium concerns are worth addressing before Phase 8 wires this to FastAPI + WhatsApp: (1) `DEFAULT_CATALOG_PATH` is fragile under non-editable installs, and (2) there is no input-length cap on untrusted merchant input. Both are defensive improvements rather than live bugs.

## Medium

### MD-01 — Fragile DEFAULT_CATALOG_PATH under non-editable installs

**File:** `src/meshek_ml/parsing/catalog.py` (DEFAULT_CATALOG_PATH definition)

`DEFAULT_CATALOG_PATH` is computed as `Path(__file__).resolve().parents[3] / "configs" / "parsing" / "products_he.yaml"`. Works for editable installs but breaks the moment the package is installed into `site-packages` as a wheel — `parents[3]` then points somewhere inside `site-packages/`. Phase 8 ships this in a FastAPI service that is likely containerized or pip-installed, so the default breaks silently at runtime.

**Fix:** Ship the YAML as package data via `importlib.resources`, or resolve from an env var with a dev fallback. Recommended: move to `src/meshek_ml/parsing/data/products_he.yaml` and load via `importlib.resources.files("meshek_ml.parsing").joinpath("data/products_he.yaml")`.

### MD-02 — No length cap on untrusted merchant input

**File:** `src/meshek_ml/parsing/parser.py` (`parse_sales_line`)

Accepts arbitrarily long text with no upper bound. Phase 8 will pipe WhatsApp merchant text through this function; a malicious/malformed webhook could push multi-megabyte payloads. The pipeline is linear but allocates several full copies per call.

**Fix:** Add a cheap guard at the top of `parse_sales_line` and a dedicated `input_too_long` error kind:

```
_MAX_INPUT_CHARS = 2048
if len(text) > _MAX_INPUT_CHARS:
    return _err("input_too_long", text)
```

## Low

### LW-01 — Dead try/except ValueError around float(numbers[0])

**File:** `src/meshek_ml/parsing/parser.py`

`numbers` comes from `_NUMBER_RE.findall` with pattern `\d+(?:\.\d+)?`. Every match is a valid float literal; `float(numbers[0])` cannot raise `ValueError`. Dead code signals the wrong mental model. Remove the try/except, keep the `<= 0` check.

### LW-02 — ProductCatalog.get() is O(n) on the default-unit hot path

**File:** `src/meshek_ml/parsing/catalog.py` (`get` method)

Linearly scans `self.products`. Called from `parse_sales_line` on the default-unit fallback path (most successful parses). Trivial at ~30 products; degrades silently as catalog grows. Build a `by_id: MappingProxyType[str, Product]` alongside `alias_index` at load time; delegate `get` to it.

## Info

### IN-01 — parse_sales_lines should accept Iterable[str]

Typed as `list[str]`; implementation accepts any iterable. Widen the type so callers can pass generators.

### IN-02 — _NUMBER_RE accepts non-ASCII Unicode digits

`\d` without `re.ASCII` matches Arabic-Indic `٢٠`, etc. May be a feature or a bug — document and pin with a test, or add `re.ASCII`.

### IN-03 — Redundant count=1 in _NUMBER_RE.sub

After `len(numbers) == 1` guard, `count=1` is harmless but redundant. Author preference.

### IN-04 — Silent greedy-first resolution for multi-product lines

No `ambiguous_product` error kind analogous to `ambiguous_quantity`. First-resolved product wins. Intentional per plan, but not documented in the module docstring. Phase 8 may bundle multiple items per line.

---

## Non-findings (verified safe)

- `yaml.safe_load` is the only YAML entry point. No `yaml.load` / `yaml.Loader` usage.
- `_NUMBER_RE` has no nested quantifiers or alternations → not vulnerable to ReDoS.
- Whitespace regexes are linear.
- `normalize_text` is pure and idempotent; tests pin this.
- No dynamic code execution or shell invocation in the parsing module.
- Catalog duplicate-alias detection correctly allows same-product re-registration while rejecting cross-product collisions.
- Frozen dataclasses + `MappingProxyType` genuinely prevent post-load mutation; tested.
- `parse_sales_line` never raises on merchant input (only on `None`, which is programmer error).

---

*Reviewed: 2026-04-14*
*Reviewer: Claude (gsd-code-reviewer)*
*Depth: standard*
