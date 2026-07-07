import pytest
import respx
from httpx import Response

from mnemo_curator.models import Finding
from mnemo_curator.semantic import SemanticResolver
from mnemo_curator.settings import Settings


def _mock_completion(content: str):
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, json={"choices": [{"message": {"content": content}}]})
    )


async def test_rewrite_returns_validated_content():
    settings = Settings(openai_api_key="key")
    original = "---\ntitle: A\nowner: team\n---\n\nTODO"

    with respx.mock:
        _mock_completion("---\ntitle: A\nowner: team\n---\n\nDocumented behavior.")

        result = await SemanticResolver(settings).rewrite(original, Finding(kind="semantic-gap"))

    assert result == "---\ntitle: A\nowner: team\n---\n\nDocumented behavior."


async def test_rewrite_rejects_empty_response():
    settings = Settings(openai_api_key="key")

    with respx.mock:
        _mock_completion("   ")

        with pytest.raises(RuntimeError, match="empty"):
            await SemanticResolver(settings).rewrite("Body", Finding(kind="semantic-gap"))


async def test_rewrite_rejects_oversized_response():
    settings = Settings(openai_api_key="key")
    original = "Body"

    with respx.mock:
        _mock_completion("x" * 60_000)

        with pytest.raises(RuntimeError, match="maximum size"):
            await SemanticResolver(settings).rewrite(original, Finding(kind="semantic-gap"))


async def test_rewrite_rejects_dropped_frontmatter():
    settings = Settings(openai_api_key="key")
    original = "---\ntitle: A\nowner: team\n---\n\nTODO"

    with respx.mock:
        _mock_completion("Just a body with no frontmatter.")

        with pytest.raises(RuntimeError, match="frontmatter"):
            await SemanticResolver(settings).rewrite(original, Finding(kind="semantic-gap"))


async def test_rewrite_requires_api_key():
    settings = Settings(openai_api_key="")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        await SemanticResolver(settings).rewrite("Body", Finding(kind="semantic-gap"))
