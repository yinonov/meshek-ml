"""Centralized exception → HTTP mapping for the meshek-ml service.

D-11 / D-12: every error response uses the envelope::

    {"error": {"code": <str>, "message": <str>, "details": <any>}}

Success responses are returned raw (no envelope) so the meshek app client
stays simple.

T-8-10: generic 500 handler returns only an opaque request_id — no stack
trace, no exception message — in the response body.  Stack traces are
logged server-side with ``exc_info=True``.

Usage in create_app()::

    from meshek_ml.service.errors import register_exception_handlers
    register_exception_handlers(app)

Research anchors:
  §Architecture Pattern 4 — canonical register_exception_handlers body
  §Error → HTTP Mapping — full table
  §Pitfall 2 — RequestValidationError must have its own handler
  §Security Domain — opaque 500, stack trace logged only
"""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from meshek_ml.forecasting.schema import SchemaValidationError
from meshek_ml.storage.merchant_store import UnknownMerchantError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TIER3_ERROR_SUBSTRING = "Tier 3 requires a loaded model"


def _safe_errors(errors: list) -> list:
    """Sanitize pydantic error dicts so they are always JSON-serializable.

    Pydantic v2 attaches the original exception object under ``error.ctx``
    (e.g. ``{"ctx": {"error": ValueError("...")}}``) which is not
    JSON-serializable.  We stringify any non-primitive values in ``ctx``
    before passing them to JSONResponse.
    """
    safe = []
    for err in errors:
        cleaned = {}
        for key, value in err.items():
            if key == "ctx" and isinstance(value, dict):
                cleaned[key] = {
                    k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                    for k, v in value.items()
                }
            elif key == "url":
                # Strip the docs URL to reduce noise; callers don't need it.
                pass
            else:
                cleaned[key] = value
        safe.append(cleaned)
    return safe


def _error_response(
    code: str,
    message: str,
    status: int,
    details=None,
) -> JSONResponse:
    """Build the canonical error envelope response."""
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception → HTTP handlers on *app*.

    Order does not matter for FastAPI exception handlers (each is keyed by
    exception class), but we register from most-specific to least-specific
    for readability.
    """

    @app.exception_handler(UnknownMerchantError)
    async def handle_unknown_merchant(
        request: Request, exc: UnknownMerchantError
    ) -> JSONResponse:
        return _error_response(
            code="merchant_not_found",
            message=str(exc) or "Merchant not found",
            status=404,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # §Pitfall 2: FastAPI wraps pydantic errors in RequestValidationError;
        # this handler intercepts them before FastAPI's default {"detail": ...}
        # format can escape.
        # Use include_url=False and strip non-serializable 'ctx' values.
        return _error_response(
            code="validation_error",
            message="Request validation failed",
            status=422,
            details=_safe_errors(exc.errors()),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation_error(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        # Pydantic ValidationError escaping out of a handler body (not wrapped
        # by FastAPI's RequestValidationError machinery).
        return _error_response(
            code="validation_error",
            message="Validation error",
            status=422,
            details=_safe_errors(exc.errors()),
        )

    @app.exception_handler(SchemaValidationError)
    async def handle_schema_validation(
        request: Request, exc: SchemaValidationError
    ) -> JSONResponse:
        return _error_response(
            code="schema_validation_error",
            message=str(exc) or "Schema validation error",
            status=422,
        )

    @app.exception_handler(RuntimeError)
    async def handle_runtime_error(
        request: Request, exc: RuntimeError
    ) -> JSONResponse:
        if _TIER3_ERROR_SUBSTRING in str(exc):
            return _error_response(
                code="model_unavailable",
                message="ML model is not loaded; Tier 3 forecasting unavailable",
                status=503,
            )
        # Not a known RuntimeError — treat as internal error.
        request_id = uuid.uuid4().hex
        logger.error(
            "Unhandled RuntimeError request_id=%s", request_id, exc_info=True
        )
        return _error_response(
            code="internal_error",
            message="An unexpected error occurred",
            status=500,
            details={"request_id": request_id},
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        request_id = uuid.uuid4().hex
        logger.error(
            "Unhandled exception request_id=%s", request_id, exc_info=True
        )
        return _error_response(
            code="internal_error",
            message="An unexpected error occurred",
            status=500,
            details={"request_id": request_id},
        )


# ---------------------------------------------------------------------------
# JSON log formatter  (D-23 — stdlib only, no new dependency)
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Standard fields: ``level``, ``name``, ``message``, ``time``.
    Any extra fields attached via the ``extra=`` kwarg on the logger call
    are merged in at the top level for easy parsing by log aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        # Merge any caller-supplied extra fields (e.g. request_id, method, …)
        # Skip standard LogRecord attributes to avoid redundancy.
        _SKIP = frozenset(logging.LogRecord.__dict__) | {
            "msg", "args", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "filename", "pathname", "module",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in _SKIP and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)
