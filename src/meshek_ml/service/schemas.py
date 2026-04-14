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
