"""POST /sales handler — dual-shape: structured items or Hebrew free text.

Plan 08-03, API-03, D-08.  Catalog migration to app.state.catalog: plan 08-04.

Partial-success semantics:
- Each failing free-text line is reported in ``skipped[]`` but the request
  still returns 200 as long as at least one line parsed.
- If ALL lines fail, return 422.

The parser catalog is loaded once at startup by ``_build_engine_lifespan``
in app.py and stored on ``app.state.catalog``.  This route reads it from
there so all routes share a single loaded catalog instance (plan 04 migration).
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Request

from meshek_ml.parsing import (
    ParsedSale,
    parse_sales_lines,
)
from meshek_ml.service.schemas import SalesRequest, SalesResponse, SkippedLine
from meshek_ml.storage.merchant_store import MerchantStore

router = APIRouter()


@router.post("/sales", response_model=SalesResponse)
def post_sales(body: SalesRequest, request: Request) -> SalesResponse:
    """Accept a POST /sales payload and persist parsed rows.

    Two shapes (D-08):
    - ``items``: structured list — persisted directly.
    - ``text``: Hebrew free text — routed through parse_sales_lines first.

    Returns ``SalesResponse(accepted_rows, skipped)`` on success (200).
    Raises 422 when all lines fail to parse.
    """
    skipped: list[SkippedLine] = []

    if body.items is not None:
        # --- structured path ---
        rows = [
            {
                "date": body.date.isoformat(),
                "merchant_id": body.merchant_id,
                "product": item.product_id,
                "quantity": item.quantity,
            }
            for item in body.items
        ]
        df = pd.DataFrame(rows)
        with MerchantStore(body.merchant_id, must_exist=True) as store:
            n = store.write_sales(df)
        return SalesResponse(accepted_rows=n, skipped=[])
    else:
        # --- free-text path ---
        catalog = request.app.state.catalog

        # Split on comma, strip whitespace, drop empty segments
        raw_lines = [seg.strip() for seg in (body.text or "").split(",")]
        lines = [ln for ln in raw_lines if ln]

        results = parse_sales_lines(lines, catalog)

        accepted: list[dict] = []
        for result in results:
            if isinstance(result, ParsedSale):
                accepted.append(
                    {
                        "date": body.date.isoformat(),
                        "merchant_id": body.merchant_id,
                        "product": result.product_id,
                        "quantity": result.quantity,
                    }
                )
            else:
                skipped.append(
                    SkippedLine(line=result.raw_text, reason=result.kind)
                )

        if not accepted:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "all_lines_failed",
                    "skipped": [s.model_dump() for s in skipped],
                },
            )

        df = pd.DataFrame(accepted)
        with MerchantStore(body.merchant_id, must_exist=True) as store:
            n = store.write_sales(df)

        return SalesResponse(accepted_rows=n, skipped=skipped)
