"""
GreenFlow AI – Request Logging Middleware
==========================================
Attaches a unique correlation-ID to every request, logs it with timing,
and exposes the ID in the response header for distributed tracing.

Usage in main.py:
    from api.middleware.request_logging import RequestLoggingMiddleware
    app.add_middleware(RequestLoggingMiddleware)
"""

from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with:
      - Unique Correlation-ID  (X-Correlation-ID header)
      - HTTP method + path + status code
      - Response time in ms
      - Client IP
    Also increments the metrics counter.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate / propagate correlation ID
        header_id = request.headers.get("X-Correlation-ID")
        if header_id:
            corr_id = str(header_id)
        else:
            u_id = str(uuid.uuid4())
            corr_id = u_id[:12] # type: ignore

        # Bind to Loguru context for this request
        with logger.contextualize(request_id=corr_id):
            t0 = time.perf_counter()
            is_error = False
            response = None
            elapsed_ms = 0.0

            try:
                response = await call_next(request)
                is_error = response.status_code >= 500
            except Exception as exc:
                is_error = True
                logger.exception("Unhandled exception in request {}: {}", corr_id, exc)
                from fastapi.responses import JSONResponse
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Internal Server Error", "request_id": corr_id}
                )
            finally:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2) # type: ignore
                path       = request.url.path

                # Skip noisy health / metrics pings from logs
                if not path.startswith("/api/v1/health"):
                    logger.info(
                        "{method} {path} → {status} ({ms}ms) [{cid}] client={ip}",
                        method = request.method,
                        path   = path,
                        status = response.status_code if response else 500,
                        ms     = elapsed_ms,
                        cid    = corr_id,
                        ip     = request.client.host if request.client else "unknown",
                    )

                # Increment metrics counter
                try:
                    from api.routes.metrics import increment_requests
                    increment_requests(path, is_error)
                except Exception:
                    pass  # metrics failure must never break the request

            # Attach correlation ID to response headers
            if response:
                response.headers["X-Correlation-ID"] = corr_id
                response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
            return response
