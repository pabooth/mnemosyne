from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/") and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            request.app.state.job_store.record_audit(
                actor=getattr(request.state, "actor", "anonymous"),
                action=f"{request.method} {request.url.path}",
                status=response.status_code,
                details={"query": str(request.url.query)},
            )
        return response
