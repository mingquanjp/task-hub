"""API middlewares for request correlation and logging."""

import logging
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a unique correlation ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid4())

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log structured information about incoming HTTP requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        is_health = request.url.path == "/health"

        try:
            response = await call_next(request)

            if not is_health:
                duration_ms = (time.perf_counter() - start_time) * 1000
                request_id = getattr(request.state, "request_id", "-")

                logger.info(
                    "HTTP %s %s completed with status %s in %.2fms",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
            return response
        except Exception:
            if not is_health:
                duration_ms = (time.perf_counter() - start_time) * 1000
                request_id = getattr(request.state, "request_id", "-")

                logger.exception(
                    "HTTP %s %s failed with unhandled exception in %.2fms",
                    request.method,
                    request.url.path,
                    duration_ms,
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": duration_ms,
                    },
                )
            raise
