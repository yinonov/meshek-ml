"""Shared Pydantic v2 request/response schemas for the meshek-ml service.

Plans 02-04 append additional models to this file.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

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
