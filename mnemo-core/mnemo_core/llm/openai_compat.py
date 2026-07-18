from openai import AsyncOpenAI

from .base import LLMProvider


class OpenAICompatProvider(LLMProvider):
    """Covers OpenAI, Azure OpenAI, DeepSeek, and any OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        token_limit = (
            {"max_completion_tokens": max_tokens}
            if self._model.startswith(("gpt-5", "o1", "o3", "o4"))
            else {"max_tokens": max_tokens}
        )
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **token_limit,
        )
        choice = resp.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        if finish_reason == "length":
            raise RuntimeError(
                f"OpenAI-compatible response was truncated at the {max_tokens}-token output limit"
            )
        content = choice.message.content or ""
        if not content.strip():
            refusal = getattr(choice.message, "refusal", None)
            detail = "refused" if refusal else f"finish reason {finish_reason or 'unknown'}"
            raise RuntimeError(f"OpenAI-compatible provider returned an empty response ({detail})")
        return content
