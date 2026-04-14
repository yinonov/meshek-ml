"""Tests for GET /health endpoint — plan 8-01-02."""
from __future__ import annotations


def test_health_with_model(app_client):
    """GET /health returns 200 with model_loaded=true when model is present."""
    response = app_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["version"] == "1.1.0"


def test_health_degraded(no_model_client):
    """GET /health returns 503 with model_loaded=false when model file is missing."""
    response = no_model_client.get("/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is False
    assert body["version"] == "1.1.0"
