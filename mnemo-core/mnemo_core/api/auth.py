from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from ..auth import auth_is_configured, bearer_token_is_valid
from ..config import Settings, get_settings


async def require_api_token(
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
