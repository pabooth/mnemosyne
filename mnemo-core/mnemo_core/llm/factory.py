from ..config import Settings, get_settings
from .anthropic import AnthropicProvider
from .base import LLMProvider
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider


def get_provider(cfg: Settings | None = None) -> LLMProvider:
    settings = get_settings() if cfg is None else cfg
    match settings.llm_provider:
        case "anthropic":
            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
        case "openai":
            return OpenAICompatProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
            )
        case "deepseek":
            return OpenAICompatProvider(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com",
                model=settings.deepseek_model,
            )
        case "ollama":
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
            )
        case _:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {settings.llm_provider!r}. "
                "Valid options: anthropic, openai, deepseek, ollama"
            )
