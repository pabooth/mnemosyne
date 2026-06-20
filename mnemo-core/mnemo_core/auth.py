import secrets

from .config import Settings, get_settings

BEARER_PREFIX = "Bearer "


def auth_is_configured(cfg: Settings | None = None) -> bool:
    settings = get_settings() if cfg is None else cfg
    return bool(settings.mnemo_api_token or settings.mnemo_api_tokens)


def bearer_token_is_valid(
    authorization: str | None,
    cfg: Settings | None = None,
) -> bool:
    cfg = get_settings() if cfg is None else cfg
    if not auth_is_configured(cfg) or not authorization:
        return False

    if not authorization.startswith(BEARER_PREFIX):
        return False

    token = authorization[len(BEARER_PREFIX):]
    if cfg.mnemo_api_token and secrets.compare_digest(token, cfg.mnemo_api_token):
        return True
    for entry in cfg.mnemo_api_tokens.split(","):
        parts = entry.strip().split(":")
        if len(parts) >= 2 and secrets.compare_digest(token, parts[1]):
            return True
    return False
