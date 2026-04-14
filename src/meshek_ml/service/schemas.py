"""Shared Pydantic v2 request/response schemas for the meshek-ml service.

Plans 02-04 append additional models to this file.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

MerchantIdStr = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""Regex-validated merchant ID.  Mirrors storage layer ``_MERCHANT_ID_PATTERN``
(D-13) to enforce 422 at the edge before any filesystem I/O (T-5-01)."""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response schema for GET /health (API-01, D-10)."""

    status: Literal["ok"] = "ok"
    model_loaded: bool
    version: str


# ---------------------------------------------------------------------------
# Merchants (API-02, plan 08-02)
# ---------------------------------------------------------------------------


class CreateMerchantRequest(BaseModel):
    """Request body for POST /merchants (D-07, D-13).

    ``merchant_id`` is optional — when omitted the handler generates a
    uuid4.hex id (32 lowercase hex chars, always valid against
    ``MerchantIdStr``).  Pydantic validates ``merchant_id`` via
    ``MerchantIdStr`` *before* any filesystem I/O, enforcing T-5-01.

    ``display_name`` maps to ``MerchantProfile.name`` in the storage layer.
    ``max_length=128`` mitigates T-8-05 (oversized display_name DoS).
    """

    merchant_id: MerchantIdStr | None = None
    display_name: str | None = Field(default=None, max_length=128)


# ---------------------------------------------------------------------------
# Sales (API-03, plan 08-03)
# ---------------------------------------------------------------------------


class SalesItem(BaseModel):
    """A single structured sales line item."""

    product_id: str = Field(min_length=1, max_length=64)
    quantity: float = Field(gt=0)
    unit: str = "unit"


class SkippedLine(BaseModel):
    """A line that failed to parse, included in partial-success responses."""

    line: str
    reason: str


class SalesRequest(BaseModel):
    """Request body for POST /sales (D-08, API-03).

    Exactly one of ``items`` or ``text`` must be provided:
    - ``items``: structured list of sale line items
    - ``text``: Hebrew free text, routed through the Phase 7 parser

    ``merchant_id`` validated via ``MerchantIdStr`` (T-5-01).
    ``text`` capped at 2048 chars matching the parser cap (T-7-02).
    """

    merchant_id: MerchantIdStr
    date: date
    items: list[SalesItem] | None = None
    text: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def exactly_one_of_items_or_text(self) -> "SalesRequest":
        if (self.items is None) == (self.text is None):
            raise ValueError("Exactly one of 'items' or 'text' must be provided")
        return self


class SalesResponse(BaseModel):
    """Response body for POST /sales (D-08)."""

    accepted_rows: int
    skipped: list[SkippedLine] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Recommend (API-04, plan 08-04)
# ---------------------------------------------------------------------------


class RecommendRequest(BaseModel):
    """Request body for POST /recommend (D-09, API-04).

    ``merchant_id`` validated via ``MerchantIdStr`` (T-5-01) so path-traversal
    is rejected at 422 before any filesystem I/O.
    """

    merchant_id: MerchantIdStr
