from ..config import Settings, get_settings
from .base import EmbeddingProvider
from .ollama import OllamaEmbedding
from .openai_compat import OpenAICompatEmbedding


def get_embedding_provider(cfg: Settings | None = None) -> EmbeddingProvider:
    settings = get_settings() if cfg is None else cfg
    match settings.embedding_provider:
        case "openai":
            return OpenAICompatEmbedding(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.embedding_openai_model,
            )
        case "ollama":
            return OllamaEmbedding(
                base_url=settings.ollama_base_url,
                model=settings.embedding_ollama_model,
            )
        case _:
            raise ValueError(
                f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r}. "
                "Valid options: openai, ollama"
            )
