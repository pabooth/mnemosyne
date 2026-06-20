import asyncio
import hashlib
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from ..config import Settings


class IntakeLimitsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cfg: Settings) -> None:
        super().__init__(app)
        self._cfg = cfg
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._semaphore = asyncio.Semaphore(max(1, cfg.request_max_concurrency))

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method != "POST" or not (
            request.url.path.startswith("/api/")
            or request.url.path == "/mcp/messages"
        ):
            return await call_next(request)

        content_length = request.headers.get("content-length")
        try:
            body_too_large = bool(
                content_length and int(content_length) > self._cfg.request_max_body_bytes
            )
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        if body_too_large:
            return JSONResponse(status_code=413, content={"detail": "Request body is too large"})

        key = self._client_key(request)
        now = time.monotonic()
        window = self._requests[key]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= max(1, self._cfg.request_rate_limit_per_minute):
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": "60"},
                content={"detail": "Rate limit exceeded"},
            )
        window.append(now)

        async with self._semaphore:
            return await call_next(request)

    @staticmethod
    def _client_key(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization:
            return hashlib.sha256(authorization.encode()).hexdigest()
        return request.client.host if request.client else "unknown"
