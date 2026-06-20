from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ...config import Settings, get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready(cfg: Settings = Depends(get_settings)) -> JSONResponse:
    checks = {
        "api_token": bool(cfg.mnemo_api_token or cfg.mnemo_api_tokens),
        "llm": _llm_is_configured(cfg),
        "github": bool(cfg.github_token and cfg.github_repo),
    }
    ready_now = all(checks.values())
    return JSONResponse(
        status_code=200 if ready_now else 503,
        content={"status": "ready" if ready_now else "not-ready", "checks": checks},
    )


def _llm_is_configured(cfg: Settings) -> bool:
    if cfg.llm_provider == "anthropic":
        return bool(cfg.anthropic_api_key)
    if cfg.llm_provider == "openai":
        return bool(cfg.openai_api_key)
    if cfg.llm_provider == "deepseek":
        return bool(cfg.deepseek_api_key)
    if cfg.llm_provider == "ollama":
        return bool(cfg.ollama_base_url)
    return False
