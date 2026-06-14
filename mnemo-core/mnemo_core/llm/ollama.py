from .openai_compat import OpenAICompatProvider


class OllamaProvider(OpenAICompatProvider):
    """Uses Ollama's OpenAI-compatible endpoint — no separate ollama package required."""

    def __init__(self, base_url: str, model: str) -> None:
        super().__init__(
            api_key="ollama",  # Ollama requires a non-empty value but ignores it
            base_url=f"{base_url.rstrip('/')}/v1",
            model=model,
        )
