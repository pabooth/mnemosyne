import secrets

from .config import Settings, get_settings

BEARER_PREFIX = "Bearer "


def auth_is_configured(cfg: Settings | None = None) -> bool:
    settings = get_settings() if cfg is None else cfg
    return bool(settings.mnemo_api_token)


def bearer_token_is_valid(
    authorization: str | None,
    cfg: Settings | None = None,
) -> bool:
    cfg = get_settings() if cfg is None else cfg
    if not cfg.mnemo_api_token or not authorization:
        return False

    if not authorization.startswith(BEARER_PREFIX):
        return False

    token = authorization[len(BEARER_PREFIX):]
    return secrets.compare_digest(token, cfg.mnemo_api_token)
