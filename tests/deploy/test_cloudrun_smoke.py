"""Env-guarded live Cloud Run smoke test (D-29, D-30).

Guards: both MESHEK_CLOUDRUN_SMOKE=1 and MESHEK_CLOUDRUN_URL must be set. Without
them the test is skipped silently, so normal CI / `uv run pytest` runs do not hit
the live URL.

Replicates the Phase 8 Docker smoke pattern against the live Cloud Run URL:
  1. POST /merchants {}                                    → 201
  2. POST /sales {merchant_id, date, text}                 → 200
  3. POST /recommend {merchant_id}                         → 200

Notes:
  - Uses urllib.request (stdlib only — no httpx dependency added to test deps)
  - Catches urllib.error.HTTPError explicitly (Phase 8 learned that urlopen raises
    on 4xx/5xx; see commit e3e8b12 context)
  - Marked @pytest.mark.integration so `-m "not integration"` excludes it

Usage:
    MESHEK_CLOUDRUN_SMOKE=1 \\
    MESHEK_CLOUDRUN_URL="$(gcloud run services describe meshek-ml \\
        --region me-west1 --format='value(status.url)')" \\
    .venv/bin/python -m pytest tests/deploy/test_cloudrun_smoke.py -x -v
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest
from datetime import date as _date

pytestmark = pytest.mark.integration

_SMOKE_ENABLED = (
    os.environ.get("MESHEK_CLOUDRUN_SMOKE") == "1"
    and bool(os.environ.get("MESHEK_CLOUDRUN_URL"))
)

_BASE_URL = (os.environ.get("MESHEK_CLOUDRUN_URL") or "").rstrip("/")
_TIMEOUT_S = 60  # cold start + model load budget


def _post(path: str, payload: dict) -> tuple[int, dict]:
    url = f"{_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            body_bytes = resp.read()
            return resp.status, json.loads(body_bytes.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AssertionError(
            f"HTTP {exc.code} from POST {url}: {body}"
        ) from exc


@pytest.mark.skipif(
    not _SMOKE_ENABLED,
    reason="Cloud Run smoke disabled (set MESHEK_CLOUDRUN_SMOKE=1 + MESHEK_CLOUDRUN_URL)",
)
def test_cloudrun_full_merchant_flow():
    # 1. Create merchant
    status, body = _post("/merchants", {})
    assert status == 201, f"expected 201 Created, got {status}: {body}"
    merchant_id = body.get("merchant_id")
    assert isinstance(merchant_id, str) and merchant_id, f"missing merchant_id: {body}"

    # 2. Post Hebrew sales line
    status, body = _post(
        "/sales",
        {
            "merchant_id": merchant_id,
            "date": _date.today().isoformat(),
            "text": "20 עגבניות, 5 מלפפונים",
        },
    )
    assert status == 200, f"expected 200 OK from /sales, got {status}: {body}"
    assert "accepted_rows" in body, f"sales response missing 'accepted_rows': {body}"
    assert isinstance(body["accepted_rows"], int) and body["accepted_rows"] >= 1, (
        f"expected accepted_rows >= 1, got {body['accepted_rows']!r}"
    )
    assert "skipped" in body, f"sales response missing 'skipped': {body}"
    assert isinstance(body["skipped"], list), (
        f"expected skipped to be a list, got {type(body['skipped']).__name__}"
    )

    # 3. Get recommendations
    status, body = _post("/recommend", {"merchant_id": merchant_id})
    assert status == 200, f"expected 200 OK from /recommend, got {status}: {body}"
    assert "recommendations" in body, (
        f"recommend response missing 'recommendations': {body}"
    )
    assert isinstance(body["recommendations"], list), (
        f"recommendations not a list: {body['recommendations']!r}"
    )
