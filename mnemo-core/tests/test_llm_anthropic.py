from unittest.mock import AsyncMock

import pytest
from anthropic.types import TextBlock, ThinkingBlock

from mnemo_core.llm.anthropic import AnthropicProvider


async def test_complete_skips_thinking_blocks():
    provider = AnthropicProvider(api_key="test", model="test-model")
    provider._client.messages.create = AsyncMock(
        return_value=AsyncMock(
            content=[
                ThinkingBlock(type="thinking", thinking="Reasoning", signature="signature"),
                TextBlock(type="text", text="The answer"),
            ]
        )
    )

    result = await provider.complete(system="System prompt", user="User prompt")

    assert result == "The answer"


async def test_complete_combines_all_text_blocks():
    provider = AnthropicProvider(api_key="test", model="test-model")
    provider._client.messages.create = AsyncMock(
        return_value=AsyncMock(
            content=[
                TextBlock(type="text", text="First"),
                TextBlock(type="text", text=" second"),
            ]
        )
    )

    result = await provider.complete(system="System prompt", user="User prompt")

    assert result == "First second"


async def test_complete_reports_output_truncation():
    provider = AnthropicProvider(api_key="test", model="test-model")
    provider._client.messages.create = AsyncMock(
        return_value=AsyncMock(
            stop_reason="max_tokens",
            content=[TextBlock(type="text", text="partial")],
        )
    )

    with pytest.raises(RuntimeError, match="truncated at the 123-token"):
        await provider.complete(system="System prompt", user="User prompt", max_tokens=123)
