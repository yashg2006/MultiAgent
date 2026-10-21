"""
HTTP middleware: a correlation id per request, and request metrics.

- Each request gets a request id (from the `X-Request-ID` header if present,
  else a new short id). It's put in the logging context so every log line of
  the request carries it, and returned in the `X-Request-ID` response header.
- Each request is counted and timed. For a normal response the timer covers
  the whole response; for a streaming response (the SSE endpoint, which stays
  open for the length of a run) it covers time to the first byte, so one long
  stream doesn't look like a multi-minute request.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.shared.observability import (
    HTTP_LATENCY,
    HTTP_REQUESTS,
    request_id_var,
    task_id_var,
)


def route_template(request: Request) -> str:
    """The matched route path (e.g. /tasks/{task_id}), not the concrete URL, so
    per-task ids don't explode the metric label set. Falls back to the raw path."""
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request_token = request_id_var.set(request_id)
        task_token = task_id_var.set(None)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(request_token)
            task_id_var.reset(task_token)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        route = route_template(request)
        HTTP_LATENCY.labels(method=request.method, route=route).observe(time.perf_counter() - start)
        HTTP_REQUESTS.labels(
            method=request.method, route=route, status=str(response.status_code)
        ).inc()
        return response


def install(app: ASGIApp) -> None:
    """Add both middlewares. Request context is added last so it runs first."""
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
