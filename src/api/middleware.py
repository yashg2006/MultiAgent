"""
HTTP middleware: a correlation id per request, and request metrics.

These are plain ASGI middlewares, not Starlette's BaseHTTPMiddleware, because
that wrapper buffers/breaks StreamingResponse - and our SSE endpoint streams
for the whole length of a run. Writing to the ASGI interface directly leaves
streaming untouched.

- Each request gets a request id (from `X-Request-ID` if present, else a new
  short id), put in the logging context so every log line of the request
  carries it, and returned in the `X-Request-ID` response header.
- Each request is counted and timed to the first response byte, so a long SSE
  stream isn't recorded as a multi-minute request.
"""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.shared.observability import (
    HTTP_LATENCY,
    HTTP_REQUESTS,
    request_id_var,
    task_id_var,
)


def _route_template(scope: Scope) -> str:
    """The matched route path (e.g. /tasks/{task_id}), set by the router after
    matching, so per-task ids don't explode the metric label set. Falls back to
    the concrete path (e.g. for 404s)."""
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else str(scope.get("path", "unknown"))


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v for k, v in scope.get("headers", [])}
        request_id = headers.get("x-request-id", b"").decode("latin-1") or uuid.uuid4().hex[:12]
        request_token = request_id_var.set(request_id)
        task_token = task_id_var.set(None)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            request_id_var.reset(request_token)
            task_id_var.reset(task_token)


class MetricsMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        recorded = False

        async def send_with_metrics(message: Message) -> None:
            nonlocal recorded
            if message["type"] == "http.response.start" and not recorded:
                recorded = True
                route = _route_template(scope)
                method = str(scope.get("method", "GET"))
                HTTP_LATENCY.labels(method=method, route=route).observe(time.perf_counter() - start)
                HTTP_REQUESTS.labels(
                    method=method, route=route, status=str(message["status"])
                ).inc()
            await send(message)

        await self.app(scope, receive, send_with_metrics)


def install(app: FastAPI) -> None:
    """Add both middlewares. Request context is added last so it runs first."""
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(RequestContextMiddleware)
