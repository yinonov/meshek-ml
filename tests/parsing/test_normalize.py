"""Tests for meshek_ml.parsing.normalize (D-07 + D-09)."""

from __future__ import annotations

import pytest

from meshek_ml.parsing.normalize import (
    UNIT_ALIASES,
    Unit,
    match_unit_token,
    normalize_text,
)


def test_strip_niqqud() -> None:
    # עֲגָבְנִיָּה (with niqqud) should normalize equal to עגבניה (without).
    assert normalize_text("עֲגָבְנִיָּה") == normalize_text("עגבניה")


def test_fold_final_letters() -> None:
    # Each final-letter form must be folded to its non-final equivalent.
    assert normalize_text("מלך").endswith("כ")
    assert not normalize_text("מלך").endswith("ך")

    assert normalize_text("עם").endswith("מ")
    assert normalize_text("מן").endswith("נ")
    assert normalize_text("כסף").endswith("פ")
    assert normalize_text("עץ").endswith("צ")


def test_lowercase_latin() -> None:
    assert normalize_text("Tomato") == "tomato"
    assert normalize_text("BANANA") == "banana"


def test_collapse_whitespace() -> None:
    assert normalize_text("  עגבניה   אדומה  ") == "עגבניה אדומה"
    assert normalize_text("a\tb\nc") == "a b c"


@pytest.mark.parametrize(
    "raw",
    [
        "עֲגָבְנִיָּה",
        "  Tomato  ",
        "  עגבניה   אדומה  ",
        "מלך",
        "ק״ג",
    ],
)
def test_idempotent(raw: str) -> None:
    once = normalize_text(raw)
    assert normalize_text(once) == once


@pytest.mark.parametrize("token", ["קג", "ק״ג", "קילו"])
def test_unit_kg_variants(token: str) -> None:
    assert match_unit_token(normalize_text(token)) is Unit.KG


def test_unit_gram() -> None:
    assert match_unit_token(normalize_text("גרם")) is Unit.GRAM


@pytest.mark.parametrize("token", ["יחידה", "יחידות"])
def test_unit_unit_variants(token: str) -> None:
    assert match_unit_token(normalize_text(token)) is Unit.UNIT


@pytest.mark.parametrize("token", ["ארגז", "ארגזים"])
def test_unit_crate_variants(token: str) -> None:
    assert match_unit_token(normalize_text(token)) is Unit.CRATE


def test_unknown_unit_returns_none() -> None:
    assert match_unit_token("banana") is None
    assert match_unit_token(normalize_text("שטויות")) is None


def test_unit_aliases_keys_are_normalized() -> None:
    # Contract: every UNIT_ALIASES key is already normalized.
    for key in UNIT_ALIASES:
        assert normalize_text(key) == key
