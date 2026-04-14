"""Hebrew text normalization primitives (D-07) and unit alias map (D-09).

Pure-stdlib utilities used by the parsing package:

* :func:`normalize_text` applies the full D-07 pipeline (niqqud strip,
  final-letter fold, Latin lowercase, whitespace collapse).
* :class:`Unit` enumerates the four canonical measurement units.
* :data:`UNIT_ALIASES` maps normalized Hebrew unit tokens to :class:`Unit`.
* :func:`match_unit_token` looks up an already-normalized token.
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum

__all__ = ["Unit", "normalize_text", "match_unit_token", "UNIT_ALIASES"]


class Unit(str, Enum):
    """Canonical measurement units (D-09)."""

    KG = "kg"
    GRAM = "gram"
    UNIT = "unit"
    CRATE = "crate"


# Hebrew final-letter → non-final fold table (D-07 step 3).
_FINAL_LETTER_FOLD = str.maketrans(
    {
        "ך": "כ",
        "ם": "מ",
        "ן": "נ",
        "ף": "פ",
        "ץ": "צ",
    }
)

# Hebrew niqqud + cantillation combining-mark range (D-07 step 2).
_NIQQUD_START = 0x0591
_NIQQUD_END = 0x05C7

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize free-text merchant input per D-07.

    Pipeline:

    1. Strip leading/trailing whitespace.
    2. NFD-decompose and drop combining marks in U+0591..U+05C7
       (Hebrew niqqud and cantillation).
    3. Fold Hebrew final-letter forms to their non-final equivalents.
    4. Lowercase Latin characters (Hebrew is caseless, so this is a no-op
       for Hebrew code points).
    5. Collapse runs of internal whitespace to a single ASCII space.
    """
    # Step 1: outer strip (inner whitespace handled in step 5).
    text = text.strip()

    # Step 2: NFD decompose, drop Hebrew combining marks.
    decomposed = unicodedata.normalize("NFD", text)
    text = "".join(
        ch for ch in decomposed if not (_NIQQUD_START <= ord(ch) <= _NIQQUD_END)
    )

    # Step 3: fold final letters.
    text = text.translate(_FINAL_LETTER_FOLD)

    # Step 4: lowercase Latin.
    text = text.lower()

    # Step 5: collapse whitespace.
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text


def _build_unit_aliases() -> dict[str, Unit]:
    """Build the alias map at module load with normalized keys (D-09)."""
    raw: dict[str, Unit] = {
        # Kilogram variants
        "קג": Unit.KG,
        "ק״ג": Unit.KG,
        "קילו": Unit.KG,
        # Gram
        "גרם": Unit.GRAM,
        # Unit / units
        "יחידה": Unit.UNIT,
        "יחידות": Unit.UNIT,
        # Crate / crates
        "ארגז": Unit.CRATE,
        "ארגזים": Unit.CRATE,
    }
    return {normalize_text(key): value for key, value in raw.items()}


UNIT_ALIASES: dict[str, Unit] = _build_unit_aliases()


def match_unit_token(token: str) -> Unit | None:
    """Look up ``token`` (already normalized) in :data:`UNIT_ALIASES`."""
    return UNIT_ALIASES.get(token)
