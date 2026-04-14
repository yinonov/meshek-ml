"""Hebrew sales-line parser (D-10..D-15).

Pure library surface that turns a single free-text merchant line like
``"20 עגבניות קג"`` into a structured :class:`ParsedSale`, or a
structured :class:`ParseError` for any invalid input. Never raises on
bad input — raises only on programmer error (``text is None``).

Algorithm
---------
1. If ``text`` is empty/whitespace → ``ParseError("empty_input")``.
2. ``norm = normalize_text(text)`` (D-07).
3. Extract numeric tokens with the anchored regex
   ``r"(?<!\\S)(\\d+(?:\\.\\d+)?)(?!\\S)"`` applied to ``norm``:

   * 0 numbers → ``ParseError("missing_quantity")``.
   * 2+ numbers → ``ParseError("ambiguous_quantity")``.
   * exactly 1 number → parse as ``float``; if ``<= 0`` →
     ``ParseError("bad_quantity")``.
4. Remove the single numeric token from ``norm`` (whole-token sub, then
   collapse whitespace).
5. Tokenize the remainder on whitespace. Walk a sliding window from
   ``catalog.max_alias_token_count`` down to 1 across every start
   position; first match via :meth:`ProductCatalog.resolve` wins. The
   outer loop starting at the largest size enforces greedy
   longest-first (D-10, D-11).
6. No product match → ``ParseError("unknown_product")``.
7. Tokens outside the matched product window are candidate unit tokens.
   First that resolves via :func:`match_unit_token` wins. If none match,
   fall back to ``catalog.get(product_id).default_unit`` (D-13).
8. Return ``ParsedSale(product_id, quantity, unit, raw_text=text)``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from meshek_ml.parsing.catalog import ProductCatalog
from meshek_ml.parsing.normalize import Unit, match_unit_token, normalize_text

__all__ = [
    "ParseErrorKind",
    "ParsedSale",
    "ParseError",
    "parse_sales_line",
    "parse_sales_lines",
]

ParseErrorKind = Literal[
    "empty_input",
    "input_too_long",
    "unknown_product",
    "missing_quantity",
    "bad_quantity",
    "ambiguous_quantity",
]


# Upper bound on untrusted merchant input length. WhatsApp/webhook payloads
# will feed arbitrary text through this parser; cap defensively so we never
# allocate multi-megabyte normalization buffers on malformed input (MD-02).
_MAX_INPUT_CHARS = 2048

# Whole-token numeric regex: integer or decimal, bordered by non-\S
# (start/end of string or whitespace). Prevents "12x" from matching and
# avoids backtracking (T-7-07).
_NUMBER_RE = re.compile(r"(?<!\S)(\d+(?:\.\d+)?)(?!\S)")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ParsedSale:
    """Successful parse of a single Hebrew sales line."""

    product_id: str
    quantity: float
    unit: Unit
    raw_text: str


@dataclass(frozen=True)
class ParseError:
    """Structured failure for a single sales line (D-15).

    Never raised — always returned. ``hint`` is an optional short
    Hebrew-friendly message; tests do not assert its contents.
    """

    kind: ParseErrorKind
    raw_text: str
    hint: str | None = None


_HINTS: dict[str, str] = {
    "empty_input": "לא התקבל טקסט",
    "input_too_long": "הטקסט ארוך מדי",
    "unknown_product": "מוצר לא מזוהה",
    "missing_quantity": "חסרה כמות",
    "bad_quantity": "כמות חייבת להיות גדולה מאפס",
    "ambiguous_quantity": "נמצאו מספר ערכים מספריים",
}


def _err(kind: ParseErrorKind, raw_text: str) -> ParseError:
    return ParseError(kind=kind, raw_text=raw_text, hint=_HINTS.get(kind))


def parse_sales_line(text: str, catalog: ProductCatalog) -> ParsedSale | ParseError:
    """Parse a single Hebrew sales line.

    Returns a :class:`ParsedSale` on success or a :class:`ParseError`
    for any recoverable failure. Raises :class:`TypeError` only on
    programmer error (``text is None``).
    """
    if text is None:  # programmer error — not merchant input
        raise TypeError("parse_sales_line: text must not be None")

    if len(text) > _MAX_INPUT_CHARS:
        return _err("input_too_long", text)

    if not text.strip():
        return _err("empty_input", text)

    norm = normalize_text(text)
    if not norm:
        return _err("empty_input", text)

    numbers = _NUMBER_RE.findall(norm)
    if len(numbers) == 0:
        # Still need to check whether the (number-less) line even points
        # at a known product, but D-15 says: no number → missing_quantity.
        return _err("missing_quantity", text)
    if len(numbers) >= 2:
        return _err("ambiguous_quantity", text)

    # _NUMBER_RE only matches ``\d+(?:\.\d+)?``, so every captured token is
    # already a valid float literal — no ValueError possible here (LW-01).
    quantity = float(numbers[0])
    if quantity <= 0:
        return _err("bad_quantity", text)

    # Strip the numeric whole-token (single substitution) then collapse.
    without_number = _NUMBER_RE.sub(" ", norm, count=1)
    without_number = _WS_RE.sub(" ", without_number).strip()

    if not without_number:
        return _err("unknown_product", text)

    tokens = without_number.split(" ")

    # Greedy longest-first alias window walk.
    max_window = max(1, min(catalog.max_alias_token_count, len(tokens)))
    match_start: int | None = None
    match_size: int | None = None
    product_id: str | None = None
    for size in range(max_window, 0, -1):
        found = False
        for start in range(0, len(tokens) - size + 1):
            candidate = " ".join(tokens[start : start + size])
            resolved = catalog.resolve(candidate)
            if resolved is not None:
                match_start = start
                match_size = size
                product_id = resolved
                found = True
                break
        if found:
            break

    if product_id is None or match_start is None or match_size is None:
        return _err("unknown_product", text)

    # Leftover tokens (not part of the matched product window) are
    # candidate unit tokens. First hit wins.
    leftover = tokens[:match_start] + tokens[match_start + match_size :]
    unit: Unit | None = None
    for tok in leftover:
        hit = match_unit_token(tok)
        if hit is not None:
            unit = hit
            break

    if unit is None:
        product = catalog.get(product_id)
        # product cannot be None: resolve() returned its id.
        assert product is not None  # noqa: S101 — invariant, not validation
        unit = product.default_unit

    return ParsedSale(
        product_id=product_id,
        quantity=quantity,
        unit=unit,
        raw_text=text,
    )


def parse_sales_lines(
    lines: list[str], catalog: ProductCatalog
) -> list[ParsedSale | ParseError]:
    """Batch helper. Same semantics as :func:`parse_sales_line` per element."""
    return [parse_sales_line(line, catalog) for line in lines]
