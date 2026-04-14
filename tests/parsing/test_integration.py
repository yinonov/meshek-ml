"""End-to-end Hebrew parsing tests against the real seed catalog (D-18).

These tests load the shipped ``configs/parsing/products_he.yaml`` via the
public API and verify every success criterion from Phase 7's testing
contract. This is the PARSE-01 / PARSE-02 closure gate.
"""

from __future__ import annotations

import pytest

from meshek_ml.parsing import (
    DEFAULT_CATALOG_PATH,
    ParsedSale,
    ParseError,
    ProductCatalog,
    Unit,
    load_catalog,
    parse_sales_line,
)


@pytest.fixture(scope="module")
def seed_catalog() -> ProductCatalog:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    # T-7-10: fail fast if seed YAML drifts away from the tomato anchor.
    if catalog.get("tomato") is None:
        pytest.fail(
            "Seed catalog missing 'tomato' product_id — integration tests "
            "anchor on tomato. Update products_he.yaml or this fixture."
        )
    return catalog


def _as_sale(result: ParsedSale | ParseError) -> ParsedSale:
    assert isinstance(result, ParsedSale), f"expected ParsedSale, got {result!r}"
    return result


def test_singular_plural_misspelling_same_id(seed_catalog: ProductCatalog) -> None:
    """Case (a): עגבנייה / עגבניה / עגבניות all resolve to 'tomato'."""
    variants = ["עגבנייה", "עגבניה", "עגבניות"]
    ids = set()
    for variant in variants:
        sale = _as_sale(parse_sales_line(f"5 {variant}", seed_catalog))
        ids.add(sale.product_id)
    assert ids == {"tomato"}


def test_number_before_and_after_order_invariant(
    seed_catalog: ProductCatalog,
) -> None:
    """Case (b): quantity-first and product-first both parse identically."""
    before = _as_sale(parse_sales_line("20 עגבניות", seed_catalog))
    after = _as_sale(parse_sales_line("עגבניות 20 קג", seed_catalog))

    assert before.product_id == "tomato"
    assert before.quantity == 20.0
    assert after.product_id == "tomato"
    assert after.quantity == 20.0
    assert after.unit == Unit.KG


def test_unknown_product_returns_structured_error(
    seed_catalog: ProductCatalog,
) -> None:
    """Case (c): a non-seed Hebrew word → ParseError(kind='unknown_product')."""
    result = parse_sales_line("5 זנב", seed_catalog)
    assert isinstance(result, ParseError)
    assert result.kind == "unknown_product"


def test_niqqud_input_parses_identically(seed_catalog: ProductCatalog) -> None:
    """Case (d): niqqud-bearing and niqqud-free forms resolve the same."""
    with_niqqud = _as_sale(parse_sales_line("5 עֲגָבְנִיָּה", seed_catalog))
    without = _as_sale(parse_sales_line("5 עגבניה", seed_catalog))
    assert with_niqqud.product_id == without.product_id == "tomato"
    assert with_niqqud.quantity == without.quantity == 5.0


def test_kg_unit_variants_all_map_to_kg(seed_catalog: ProductCatalog) -> None:
    """Case (e): קג / ק״ג / קילו all normalize to Unit.KG."""
    for line in ("5 קג עגבניות", "5 ק״ג עגבניות", "5 קילו עגבניות"):
        sale = _as_sale(parse_sales_line(line, seed_catalog))
        assert sale.unit == Unit.KG, f"line {line!r} did not map to KG"
        assert sale.product_id == "tomato"


def test_empty_and_whitespace(seed_catalog: ProductCatalog) -> None:
    """Case (f): empty / whitespace-only → ParseError(kind='empty_input')."""
    for text in ("", "   "):
        result = parse_sales_line(text, seed_catalog)
        assert isinstance(result, ParseError)
        assert result.kind == "empty_input"


def test_public_api_importable() -> None:
    """The public surface is reachable directly from meshek_ml.parsing."""
    from meshek_ml.parsing import (  # noqa: F401 — import is the assertion
        DEFAULT_CATALOG_PATH,
        ParsedSale,
        ParseError,
        ProductCatalog,
        Unit,
        load_catalog,
        parse_sales_line,
    )

    assert callable(parse_sales_line)
    assert callable(load_catalog)
