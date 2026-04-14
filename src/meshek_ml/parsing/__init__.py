"""Hebrew input parsing package — public API.

Phase 7 Plan 04: expose the full parsing surface as a single import so
Phase 8 (FastAPI route) can do ``from meshek_ml.parsing import ...``
without touching submodules.
"""

from __future__ import annotations

from meshek_ml.parsing.catalog import (
    DEFAULT_CATALOG_PATH,
    CatalogError,
    Product,
    ProductCatalog,
    load_catalog,
)
from meshek_ml.parsing.normalize import Unit, normalize_text
from meshek_ml.parsing.parser import (
    ParsedSale,
    ParseError,
    parse_sales_line,
    parse_sales_lines,
)

__all__ = [
    "Unit",
    "normalize_text",
    "Product",
    "ProductCatalog",
    "CatalogError",
    "load_catalog",
    "DEFAULT_CATALOG_PATH",
    "ParsedSale",
    "ParseError",
    "parse_sales_line",
    "parse_sales_lines",
]
