"""Category defaults config loader for Tier 1 recommendations.

Loads ``configs/recommendation/category_defaults.yaml`` via ``yaml.safe_load``
(T-6-03 mitigation: never ``yaml.load``) and validates into a pydantic model.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class CategoryDefaultProduct(BaseModel):
    product_id: str
    default_quantity: float
    unit: str


class CategoryDefaultsConfig(BaseModel):
    products: list[CategoryDefaultProduct]


def load_category_defaults(path: Path) -> CategoryDefaultsConfig:
    """Parse a category-defaults YAML file into a validated config model.

    Raises:
        FileNotFoundError: if ``path`` does not exist. Callers must handle
            or propagate — the loader intentionally does not swallow it.
    """
    with open(path, "rb") as fh:
        raw = yaml.safe_load(fh)
    return CategoryDefaultsConfig.model_validate(raw)
