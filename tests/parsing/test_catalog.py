"""Tests for :mod:`meshek_ml.parsing.catalog` (Plan 07-02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from meshek_ml.parsing.catalog import (
    CatalogError,
    Product,
    ProductCatalog,
    DEFAULT_CATALOG_PATH,
    load_catalog,
)
from meshek_ml.parsing.normalize import Unit, normalize_text


@pytest.fixture(scope="module")
def seed_catalog() -> ProductCatalog:
    return load_catalog(DEFAULT_CATALOG_PATH)


def test_default_catalog_path_exists() -> None:
    assert DEFAULT_CATALOG_PATH.is_file(), (
        f"Seed catalog missing at {DEFAULT_CATALOG_PATH}"
    )


def test_seed_has_expected_size(seed_catalog: ProductCatalog) -> None:
    # Seed target ~30 products; accept >= 25 as per acceptance_criteria.
    assert len(seed_catalog.products) >= 25


def test_every_product_has_unit(seed_catalog: ProductCatalog) -> None:
    for product in seed_catalog.products:
        assert isinstance(product.default_unit, Unit)


def test_every_product_has_misspelling_alias(seed_catalog: ProductCatalog) -> None:
    # Each product must ship at least one alias beyond the canonical display,
    # which per D-06 includes at least one common misspelling. We enforce the
    # floor as "≥2 explicit aliases" (singular/plural + misspelling).
    for product in seed_catalog.products:
        assert len(product.aliases) >= 2, (
            f"Product {product.product_id!r} has too few aliases: {product.aliases}"
        )


def test_alias_index_size(seed_catalog: ProductCatalog) -> None:
    # Index must contain at least every explicit alias (plus implicit he/en),
    # and must be strictly larger than the product count.
    assert len(seed_catalog.alias_index) >= len(seed_catalog.products) * 2


def test_aliases_indexed_normalized(seed_catalog: ProductCatalog) -> None:
    # Resolve singular, plural, and misspelling variants of "tomato".
    assert seed_catalog.resolve(normalize_text("עגבנייה")) == "tomato"
    assert seed_catalog.resolve(normalize_text("עגבניה")) == "tomato"
    assert seed_catalog.resolve(normalize_text("עגבניות")) == "tomato"


def test_resolve_unknown_returns_none(seed_catalog: ProductCatalog) -> None:
    assert seed_catalog.resolve("banana-not-a-hebrew-token-xyz") is None


def test_get_by_product_id(seed_catalog: ProductCatalog) -> None:
    tomato = seed_catalog.get("tomato")
    assert tomato is not None
    assert tomato.display_en == "tomato"
    assert seed_catalog.get("not-a-real-id") is None


def test_max_alias_token_count_at_least_two(seed_catalog: ProductCatalog) -> None:
    # bell_pepper ships "פלפל אדום"; potato ships "תפוח אדמה".
    assert seed_catalog.max_alias_token_count >= 2


def test_implicit_display_en_indexed(seed_catalog: ProductCatalog) -> None:
    assert seed_catalog.resolve(normalize_text("cucumber")) == "cucumber"


def test_duplicate_alias_raises(tmp_path: Path) -> None:
    dup_yaml = """
products:
  - id: tomato
    display_he: "עגבנייה"
    display_en: "tomato"
    category: vegetable
    default_unit: kg
    aliases:
      - "אדום"
  - id: apple
    display_he: "תפוח"
    display_en: "apple"
    category: fruit
    default_unit: kg
    aliases:
      - "אדום"
"""
    path = tmp_path / "dup.yaml"
    path.write_text(dup_yaml, encoding="utf-8")
    with pytest.raises(CatalogError, match="Duplicate alias"):
        load_catalog(path)


def test_invalid_unit_raises(tmp_path: Path) -> None:
    bad = """
products:
  - id: tomato
    display_he: "עגבנייה"
    display_en: "tomato"
    category: vegetable
    default_unit: pounds
    aliases:
      - "עגבניה"
"""
    path = tmp_path / "bad.yaml"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(CatalogError, match="invalid default_unit"):
        load_catalog(path)


def test_missing_top_level_products_raises(tmp_path: Path) -> None:
    path = tmp_path / "empty.yaml"
    path.write_text("other: 1\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="products"):
        load_catalog(path)


def test_catalog_is_frozen(seed_catalog: ProductCatalog) -> None:
    # Product / ProductCatalog are frozen dataclasses: assignment raises.
    with pytest.raises(Exception):
        seed_catalog.products[0].product_id = "mutated"  # type: ignore[misc]
