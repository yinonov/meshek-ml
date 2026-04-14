"""Per-request middleware: request_id injection + structured JSON access logging.

D-23: each request emits one structured log line with::

    {request_id, method, path, status, duration_ms}

T-8-13: the ``X-Request-ID`` response header lets clients correlate an
error back to a server-side log line without any secrets leaking.

Implementation notes:
- Uses Starlette's ``BaseHTTPMiddleware`` — compatible with FastAPI.
- ``request.state.request_id`` is set early so exception handlers can
  read it when building 500 envelopes.  (The errors.py handlers generate
  their own uuid4 because the middleware's ``dispatch`` still runs the
  ``call_next`` path even after an exception handler intercepts the error,
  but setting it on state costs nothing and future callers may use it.)
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Inject request_id into state, add X-Request-ID response header,
    and emit a structured access-log line after each request.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.monotonic()

        response: Response = await call_next(request)

        duration_ms = int((time.monotonic() - start) * 1000)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
