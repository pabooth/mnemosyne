from ..config import Settings, get_settings
from .anthropic import AnthropicProvider
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider


def get_provider(cfg: Settings | None = None) -> LLMProvider:
    settings = get_settings() if cfg is None else cfg
    return get_provider_for(
        settings.main_llm_provider,
        settings.main_llm_model,
        settings,
    )


def get_provider_for(
    provider: str,
    model: str,
    cfg: Settings | None = None,
) -> LLMProvider:
    settings = get_settings() if cfg is None else cfg
    match provider:
        case "anthropic":
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=model,
            )
        case "openai":
            return OpenAICompatProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=model,
            )
        case "deepseek":
            return OpenAICompatProvider(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com",
                model=model,
            )
        case "xai":
            return OpenAICompatProvider(
                api_key=settings.xai_api_key,
                base_url=settings.xai_base_url,
                model=model,
            )
        case "gemini":
            return OpenAICompatProvider(
                api_key=settings.gemini_api_key,
                base_url=settings.gemini_base_url,
                model=model,
            )
        case "ollama":
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=model,
            )
        case _:
            raise ValueError(
                f"Unknown LLM provider: {provider!r}. "
                "Valid options: anthropic, openai, deepseek, xai, gemini, ollama"
            )
