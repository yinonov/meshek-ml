"""Tests for centralized error handling and structured logging (plan 08-05).

D-11 / D-12: every error path produces {error: {code, message, details?}} envelope.
D-23: every request logs a structured JSON line with request_id, method, path,
      status, duration_ms.
T-8-10: stack traces never appear in response bodies.
"""
from __future__ import annotations

import logging


# ---------------------------------------------------------------------------
# 404 envelope — UnknownMerchantError
# ---------------------------------------------------------------------------


def test_404_envelope(app_client):
    """POST /sales for an unknown merchant returns 404 with error envelope."""
    resp = app_client.post(
        "/sales",
        json={
            "merchant_id": "never_created",
            "date": "2026-04-14",
            "items": [{"product_id": "tomato", "quantity": 10, "unit": "kg"}],
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "merchant_not_found"
    assert isinstance(body["error"]["message"], str)


# ---------------------------------------------------------------------------
# 422 envelope — pydantic / RequestValidationError
# ---------------------------------------------------------------------------


def test_422_envelope(app_client):
    """POST /merchants with invalid merchant_id returns 422 with error envelope."""
    resp = app_client.post("/merchants", json={"merchant_id": "../etc"})
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["message"], str)
    assert "details" in body["error"]


def test_422_envelope_missing_field(app_client):
    """POST /recommend with empty body → 422 via RequestValidationError path."""
    resp = app_client.post("/recommend", json={})
    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "validation_error"
    assert "details" in body["error"]


# ---------------------------------------------------------------------------
# 503 envelope — RuntimeError (Tier 3 no-model)
# ---------------------------------------------------------------------------


def test_503_envelope(no_model_client, data_dir):
    """Tier 3 with no model → 503 with error envelope."""
    import pandas as pd

    from meshek_ml.storage import MerchantProfile, MerchantStore

    # Seed a merchant with 20 days of sales so engine routes to Tier 3.
    with MerchantStore("err_deg_t3") as store:
        store.create_profile(MerchantProfile(merchant_id="err_deg_t3"))
        dates = pd.date_range(end="2026-04-13", periods=20, freq="D")
        rows = []
        for d in dates:
            for product in ["tomato", "cucumber"]:
                rows.append(
                    {
                        "date": d,
                        "merchant_id": "err_deg_t3",
                        "product": product,
                        "quantity": 10.0,
                    }
                )
        store.write_sales(pd.DataFrame(rows))

    resp = no_model_client.post("/recommend", json={"merchant_id": "err_deg_t3"})
    assert resp.status_code == 503
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "model_unavailable"
    assert isinstance(body["error"]["message"], str)


# ---------------------------------------------------------------------------
# 500 envelope — generic exception (opaque, no stack trace)
# ---------------------------------------------------------------------------


def test_500_envelope_opaque_request_id(app_client, monkeypatch):
    """Generic exception → 500 with opaque request_id; no internal string leaked."""
    from meshek_ml.recommendation.engine import RecommendationEngine

    def _raise(merchant_id):  # noqa: ARG001
        raise ValueError("boom")

    monkeypatch.setattr(RecommendationEngine, "recommend", _raise)

    resp = app_client.post("/recommend", json={"merchant_id": "some_merchant"})
    assert resp.status_code == 500
    body = resp.json()
    # Envelope structure
    assert "error" in body
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred"
    # No internal info leakage (T-8-10)
    assert "boom" not in resp.text
    # request_id must be a 32-char hex string
    request_id = body["error"]["details"]["request_id"]
    assert len(request_id) == 32
    assert all(c in "0123456789abcdef" for c in request_id)


# ---------------------------------------------------------------------------
# Structured log line — D-23
# ---------------------------------------------------------------------------


def test_structured_log_line(app_client, caplog):
    """Every request emits a structured JSON log line with the five required fields."""
    with caplog.at_level(logging.INFO, logger="meshek_ml.service.middleware"):
        resp = app_client.get("/health")

    assert resp.status_code == 200

    # Find the log record emitted by the middleware.
    middleware_records = [
        r for r in caplog.records if r.name == "meshek_ml.service.middleware"
    ]
    assert len(middleware_records) >= 1, "No middleware log records found"

    record = middleware_records[-1]
    # The middleware must stash these fields in the extra dict.
    assert hasattr(record, "request_id"), "request_id missing from log record"
    assert hasattr(record, "method"), "method missing from log record"
    assert hasattr(record, "path"), "path missing from log record"
    assert hasattr(record, "status"), "status missing from log record"
    assert hasattr(record, "duration_ms"), "duration_ms missing from log record"

    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status == 200
    assert record.duration_ms >= 0


# ---------------------------------------------------------------------------
# Task 8-05-02: dedicated 404 on UnknownMerchantError via /recommend
# ---------------------------------------------------------------------------


def test_unknown_merchant(app_client):
    """POST /recommend for a merchant that was never created → 404 with envelope."""
    resp = app_client.post("/recommend", json={"merchant_id": "merchant_never_created"})
    assert resp.status_code == 404
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "merchant_not_found"
    assert isinstance(body["error"]["message"], str)
