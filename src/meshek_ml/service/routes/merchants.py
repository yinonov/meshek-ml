"""POST /merchants route — API-02 (plan 08-02).

Design notes:
- Sync ``def`` handler (D-05): storage is stdlib sqlite3, no asyncio benefit.
- ``MerchantIdStr`` validation in ``CreateMerchantRequest`` fires *before*
  ``MerchantStore`` is instantiated, enforcing T-5-01 (path traversal) at
  the Pydantic layer (422 returned with zero filesystem I/O).
- When ``merchant_id`` is omitted the handler generates ``uuid.uuid4().hex``
  (32 lowercase hex chars), which trivially satisfies ``_MERCHANT_ID_PATTERN``
  (D-07).
- Response is the raw ``MerchantProfile`` pydantic model (D-06, D-12) — no
  envelope wrapper.
- ``display_name`` from the request maps to ``MerchantProfile.name`` in the
  storage layer (the storage model predates the API naming convention).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter
from meshek_ml.storage.merchant_store import MerchantProfile, MerchantStore
from meshek_ml.service.schemas import CreateMerchantRequest

router = APIRouter()


@router.post("/merchants", status_code=201, response_model=MerchantProfile)
def create_merchant(body: CreateMerchantRequest) -> MerchantProfile:
    """Create a new merchant profile and return the stored ``MerchantProfile``.

    If ``body.merchant_id`` is ``None``, a uuid4.hex id is generated
    server-side (D-07).  The regex guard in ``CreateMerchantRequest`` ensures
    the id (caller-supplied or auto-generated) is safe for filesystem use
    before ``MerchantStore`` is ever touched (T-5-01).
    """
    merchant_id = body.merchant_id if body.merchant_id is not None else uuid.uuid4().hex
    profile = MerchantProfile(merchant_id=merchant_id, name=body.display_name)
    with MerchantStore(merchant_id) as store:
        return store.create_profile(profile)
