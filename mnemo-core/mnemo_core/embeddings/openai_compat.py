from openai import AsyncOpenAI

from .base import EmbeddingProvider


class OpenAICompatEmbedding(EmbeddingProvider):
    """Covers OpenAI, Azure OpenAI, and any OpenAI-compatible embeddings endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]
