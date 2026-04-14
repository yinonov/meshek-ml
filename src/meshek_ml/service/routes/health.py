"""GET /health endpoint — API-01, D-10."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from meshek_ml.service.schemas import HealthResponse, SERVICE_VERSION

router = APIRouter()


@router.get("/health")
def get_health(request: Request) -> JSONResponse:
    """Return service health status.

    Reads ``app.state.ml`` (populated by the lifespan factory).
    Returns 200 when the model is loaded, 503 when in degraded mode.
    """
    ml = getattr(request.app.state, "ml", None)
    model_loaded = ml is not None
    status_code = 200 if model_loaded else 503
    return JSONResponse(
        content=HealthResponse(
            model_loaded=model_loaded,
            version=SERVICE_VERSION,
        ).model_dump(),
        status_code=status_code,
    )
