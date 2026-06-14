from openai import AsyncOpenAI

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    """Uses Ollama's OpenAI-compatible endpoint — no separate ollama package required."""

    def __init__(self, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(
            api_key="ollama",  # Ollama requires a non-empty value but ignores it
            base_url=f"{base_url.rstrip('/')}/v1",
        )
        self._model = model

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content
