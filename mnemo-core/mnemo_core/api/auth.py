import hashlib
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ..auth import auth_is_configured, bearer_token_is_valid
from ..config import Settings, get_settings


async def require_api_token(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    cfg: Settings = Depends(get_settings),
) -> None:
    if not auth_is_configured(cfg):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MNEMO_API_TOKEN is not configured",
        )

    if not bearer_token_is_valid(authorization, cfg):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    actor, role = _identity_for_token(authorization or "", cfg)
    request.state.actor = actor
    request.state.role = role


def _identity_for_token(authorization: str, cfg: Settings) -> tuple[str, str]:
    token = authorization.removeprefix("Bearer ")
    for entry in cfg.mnemo_api_tokens.split(","):
        parts = entry.strip().split(":")
        if len(parts) >= 2 and secrets_compare(token, parts[1]):
            return parts[0], parts[2] if len(parts) >= 3 else "submitter"
    return f"token-{hashlib.sha256(token.encode()).hexdigest()[:12]}", "admin"


def secrets_compare(left: str, right: str) -> bool:
    from secrets import compare_digest

    return compare_digest(left, right)


async def require_admin(request: Request) -> None:
    if getattr(request.state, "role", "") != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
