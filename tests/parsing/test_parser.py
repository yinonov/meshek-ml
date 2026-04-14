"""Tests for :mod:`meshek_ml.parsing.parser` (Plan 07-03)."""

from __future__ import annotations

from pathlib import Path

import pytest

from meshek_ml.parsing.catalog import ProductCatalog, load_catalog
from meshek_ml.parsing.normalize import Unit
from meshek_ml.parsing.parser import (
    ParsedSale,
    ParseError,
    parse_sales_line,
    parse_sales_lines,
)


TEST_CATALOG_YAML = """
products:
  - id: tomato
    display_he: עגבנייה
    display_en: tomato
    category: vegetable
    default_unit: kg
    aliases:
      - עגבנייה
      - עגבניה
      - עגבניות
  - id: cucumber
    display_he: מלפפון
    display_en: cucumber
    category: vegetable
    default_unit: kg
    aliases:
      - מלפפון
      - מלפפונים
  - id: bell_pepper
    display_he: פלפל אדום
    display_en: bell pepper
    category: vegetable
    default_unit: kg
    aliases:
      - פלפל
      - פלפלים
      - פלפל אדום
  - id: watermelon
    display_he: אבטיח
    display_en: watermelon
    category: fruit
    default_unit: unit
    aliases:
      - אבטיח
"""


@pytest.fixture(scope="module")
def cat(tmp_path_factory: pytest.TempPathFactory) -> ProductCatalog:
    tmp: Path = tmp_path_factory.mktemp("parser_catalog")
    yaml_path = tmp / "products.yaml"
    yaml_path.write_text(TEST_CATALOG_YAML, encoding="utf-8")
    return load_catalog(yaml_path)


def test_number_before_name(cat: ProductCatalog) -> None:
    result = parse_sales_line("20 עגבניות", cat)
    assert isinstance(result, ParsedSale)
    assert result.product_id == "tomato"
    assert result.quantity == 20.0
    assert result.unit is Unit.KG
    assert result.raw_text == "20 עגבניות"


def test_number_after_name_with_unit(cat: ProductCatalog) -> None:
    result = parse_sales_line("עגבניות 20 קג", cat)
    assert isinstance(result, ParsedSale)
    assert result.product_id == "tomato"
    assert result.quantity == 20.0
    assert result.unit is Unit.KG


def test_decimal_quantity(cat: ProductCatalog) -> None:
    result = parse_sales_line("1.5 קג מלפפון", cat)
    assert isinstance(result, ParsedSale)
    assert result.quantity == 1.5
    assert result.unit is Unit.KG
    assert result.product_id == "cucumber"


def test_niqqud_stripped_equivalent(cat: ProductCatalog) -> None:
    """Niqqud-bearing input normalizes to the same product (D-07)."""
    plain = parse_sales_line("2 עגבניה", cat)
    with_niqqud = parse_sales_line("2 עֲגַבְנִיָּה", cat)
    assert isinstance(plain, ParsedSale)
    assert isinstance(with_niqqud, ParsedSale)
    assert plain.product_id == with_niqqud.product_id == "tomato"
    assert plain.quantity == with_niqqud.quantity == 2.0


def test_default_unit_from_catalog(cat: ProductCatalog) -> None:
    result = parse_sales_line("3 אבטיח", cat)
    assert isinstance(result, ParsedSale)
    assert result.product_id == "watermelon"
    assert result.unit is Unit.UNIT


def test_greedy_longest_first(cat: ProductCatalog) -> None:
    """Multi-word alias 'פלפל אדום' wins over single-word 'פלפל'."""
    result = parse_sales_line("10 פלפל אדום", cat)
    assert isinstance(result, ParsedSale)
    assert result.product_id == "bell_pepper"
    assert result.quantity == 10.0


def test_single_word_alias_still_resolves(cat: ProductCatalog) -> None:
    result = parse_sales_line("5 פלפל", cat)
    assert isinstance(result, ParsedSale)
    assert result.product_id == "bell_pepper"


def test_empty_input(cat: ProductCatalog) -> None:
    result = parse_sales_line("   ", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "empty_input"
    assert result.raw_text == "   "


def test_unknown_product(cat: ProductCatalog) -> None:
    result = parse_sales_line("10 בננה", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "unknown_product"


def test_missing_quantity(cat: ProductCatalog) -> None:
    result = parse_sales_line("עגבניות", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "missing_quantity"


def test_bad_quantity_zero(cat: ProductCatalog) -> None:
    result = parse_sales_line("0 עגבניות", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "bad_quantity"


def test_bad_quantity_negative(cat: ProductCatalog) -> None:
    # Leading '-' is not matched by the digit regex, so '-3' becomes a
    # standalone non-numeric token → no number → missing_quantity.
    # Either outcome is acceptable per the plan; we assert the chosen
    # semantics here.
    result = parse_sales_line("-3 עגבניות", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "missing_quantity"


def test_ambiguous_quantity(cat: ProductCatalog) -> None:
    result = parse_sales_line("20 עגבניות 5", cat)
    assert isinstance(result, ParseError)
    assert result.kind == "ambiguous_quantity"


def test_input_too_long(cat: ProductCatalog) -> None:
    """Inputs longer than the module cap short-circuit to input_too_long (MD-02)."""
    huge = "20 עגבניות " + ("א" * 3000)
    result = parse_sales_line(huge, cat)
    assert isinstance(result, ParseError)
    assert result.kind == "input_too_long"
    assert result.raw_text == huge


def test_never_raises_on_garbage(cat: ProductCatalog) -> None:
    result = parse_sales_line("!!", cat)
    assert isinstance(result, ParseError)


def test_raises_type_error_on_none(cat: ProductCatalog) -> None:
    with pytest.raises(TypeError):
        parse_sales_line(None, cat)  # type: ignore[arg-type]


def test_batch_mixed(cat: ProductCatalog) -> None:
    results = parse_sales_lines(["20 עגבניות", "", "10 בננה"], cat)
    assert len(results) == 3
    assert isinstance(results[0], ParsedSale)
    assert results[0].product_id == "tomato"
    assert isinstance(results[1], ParseError)
    assert results[1].kind == "empty_input"
    assert isinstance(results[2], ParseError)
    assert results[2].kind == "unknown_product"
