"""Frozen product catalog with a prebuilt normalized alias index (D-03..D-06).

Loaded once from the packaged ``data/products_he.yaml`` via :func:`load_catalog`.
Every alias (plus implicit ``display_he`` / ``display_en``) is passed through
:func:`meshek_ml.parsing.normalize.normalize_text` at build time so runtime
resolution is a single ``dict.get`` (see Plan 03's greedy matcher).

Duplicate normalized aliases across different products raise
:class:`CatalogError` eagerly — silent overwrites would produce wrong mappings
(T-7-04). YAML is parsed via ``yaml.safe_load`` only (T-7-03).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib.resources import files as _pkg_files
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from meshek_ml.parsing.normalize import Unit, normalize_text

__all__ = [
    "CatalogError",
    "Product",
    "ProductCatalog",
    "load_catalog",
    "DEFAULT_CATALOG_PATH",
]


def _resolve_default_catalog_path() -> Path:
    """Locate ``products_he.yaml`` across both wheel and editable layouts.

    Preferred: packaged resource at ``meshek_ml/parsing/data/products_he.yaml``
    resolved via :mod:`importlib.resources`, which works for wheels installed
    into ``site-packages`` (MD-01).

    Fallback: the legacy repo-root ``configs/parsing/products_he.yaml`` path,
    kept as a safety net for older editable checkouts where the YAML has not
    yet been moved into the package tree.
    """
    try:
        packaged = _pkg_files("meshek_ml.parsing").joinpath("data/products_he.yaml")
        packaged_path = Path(str(packaged))
        if packaged_path.is_file():
            return packaged_path
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        pass

    # Editable-install safety net: repo-root ``configs/parsing`` layout.
    legacy = Path(__file__).resolve().parents[3] / "configs" / "parsing" / "products_he.yaml"
    return legacy


DEFAULT_CATALOG_PATH: Path = _resolve_default_catalog_path()


class CatalogError(ValueError):
    """Raised when the YAML catalog is malformed or has duplicate aliases."""


@dataclass(frozen=True)
class Product:
    """A single canonical product entry (D-03)."""

    product_id: str
    display_he: str
    display_en: str
    category: str
    default_unit: Unit
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ProductCatalog:
    """Immutable catalog with a prebuilt normalized alias → product_id index."""

    products: tuple[Product, ...]
    alias_index: MappingProxyType[str, str]
    by_id: MappingProxyType[str, Product]
    max_alias_token_count: int = field(default=0)

    def resolve(self, normalized_alias: str) -> str | None:
        """Return canonical ``product_id`` for a normalized alias, or None."""
        return self.alias_index.get(normalized_alias)

    def get(self, product_id: str) -> Product | None:
        """Return :class:`Product` by canonical id, or None (O(1), LW-02)."""
        return self.by_id.get(product_id)


def _coerce_unit(raw: Any, product_id: str) -> Unit:
    if not isinstance(raw, str):
        raise CatalogError(
            f"Product {product_id!r}: default_unit must be a string, got {type(raw).__name__}"
        )
    try:
        return Unit(raw)
    except ValueError as exc:
        valid = ", ".join(u.value for u in Unit)
        raise CatalogError(
            f"Product {product_id!r}: invalid default_unit {raw!r} (valid: {valid})"
        ) from exc


def _register_alias(
    index: dict[str, str],
    raw_alias: str,
    product_id: str,
) -> None:
    """Normalize and insert an alias, raising on duplicate assignment."""
    norm = normalize_text(raw_alias)
    if not norm:
        raise CatalogError(
            f"Product {product_id!r}: alias {raw_alias!r} is empty after normalization"
        )
    existing = index.get(norm)
    if existing is not None and existing != product_id:
        raise CatalogError(
            f"Duplicate alias {norm!r}: {existing} vs {product_id}"
        )
    index[norm] = product_id


def load_catalog(path: Path) -> ProductCatalog:
    """Load + validate a YAML product catalog.

    Raises:
        CatalogError: on any structural, unit, or duplicate-alias problem.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CatalogError(f"Could not read catalog at {path}: {exc}") from exc

    raw = yaml.safe_load(text)
    if not isinstance(raw, dict) or "products" not in raw:
        raise CatalogError(
            f"Catalog at {path} must be a mapping with a top-level 'products' key"
        )
    entries = raw["products"]
    if not isinstance(entries, list) or not entries:
        raise CatalogError(
            f"Catalog at {path}: 'products' must be a non-empty list"
        )

    products: list[Product] = []
    alias_index: dict[str, str] = {}

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CatalogError(f"Catalog entry #{idx} is not a mapping")

        required = ("id", "display_he", "display_en", "category", "default_unit")
        for key in required:
            if key not in entry:
                raise CatalogError(
                    f"Catalog entry #{idx} missing required field {key!r}"
                )

        product_id = entry["id"]
        if not isinstance(product_id, str) or not product_id:
            raise CatalogError(f"Catalog entry #{idx} has invalid id {product_id!r}")

        default_unit = _coerce_unit(entry["default_unit"], product_id)

        raw_aliases = entry.get("aliases") or []
        if not isinstance(raw_aliases, list):
            raise CatalogError(
                f"Product {product_id!r}: 'aliases' must be a list"
            )

        display_he = entry["display_he"]
        display_en = entry["display_en"]
        category = entry["category"]
        if not isinstance(display_he, str) or not isinstance(display_en, str):
            raise CatalogError(
                f"Product {product_id!r}: display_he/display_en must be strings"
            )
        if not isinstance(category, str):
            raise CatalogError(f"Product {product_id!r}: category must be a string")

        product = Product(
            product_id=product_id,
            display_he=display_he,
            display_en=display_en,
            category=category,
            default_unit=default_unit,
            aliases=tuple(str(a) for a in raw_aliases),
        )
        products.append(product)

        # Explicit aliases first, then implicit display_he/display_en.
        for alias in product.aliases:
            _register_alias(alias_index, alias, product_id)
        _register_alias(alias_index, display_he, product_id)
        _register_alias(alias_index, display_en, product_id)

    max_alias_token_count = (
        max((len(key.split()) for key in alias_index), default=0)
    )

    by_id: dict[str, Product] = {p.product_id: p for p in products}

    return ProductCatalog(
        products=tuple(products),
        alias_index=MappingProxyType(alias_index),
        by_id=MappingProxyType(by_id),
        max_alias_token_count=max_alias_token_count,
    )
