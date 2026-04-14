"""Tests for meshek_ml.recommendation.config (Phase 6 Plan 01)."""
from __future__ import annotations

from pathlib import Path

import pytest

from meshek_ml.recommendation.config import (
    CategoryDefaultsConfig,
    load_category_defaults,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_YAML_PATH = _REPO_ROOT / "configs" / "recommendation" / "category_defaults.yaml"


def test_load_category_defaults():
    cfg = load_category_defaults(_YAML_PATH)
    assert isinstance(cfg, CategoryDefaultsConfig)
    assert len(cfg.products) >= 3
    # Each product has required fields.
    for p in cfg.products:
        assert p.product_id
        assert p.default_quantity > 0
        assert p.unit


def test_load_category_defaults_missing_file(tmp_path: Path):
    missing = tmp_path / "does_not_exist.yaml"
    with pytest.raises(FileNotFoundError):
        load_category_defaults(missing)
