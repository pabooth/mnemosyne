from unittest.mock import AsyncMock

import pytest

from mnemo_core.api.deps import build_adversarial_reviewer
from mnemo_core.config import Settings
from mnemo_core.evaluation import CASES
from mnemo_core.llm.anthropic import AnthropicProvider
from mnemo_core.llm.factory import get_provider
from mnemo_core.llm.ollama import OllamaProvider
from mnemo_core.llm.openai_compat import OpenAICompatProvider


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(main_llm_provider="anthropic", anthropic_api_key="test"), AnthropicProvider),
        (Settings(main_llm_provider="openai", openai_api_key="test"), OpenAICompatProvider),
        (Settings(main_llm_provider="deepseek", deepseek_api_key="test"), OpenAICompatProvider),
        (Settings(main_llm_provider="xai", xai_api_key="test"), OpenAICompatProvider),
        (Settings(main_llm_provider="gemini", gemini_api_key="test"), OpenAICompatProvider),
        (Settings(main_llm_provider="ollama"), OllamaProvider),
    ],
)
def test_provider_factory_contract(settings, expected):
    provider = get_provider(settings)
    assert isinstance(provider, expected)
    assert callable(provider.complete)


def test_provider_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unsupported LLM provider families: unknown"):
        Settings(main_llm_provider="unknown")


def test_main_model_is_independent_from_provider_credentials():
    provider = get_provider(
        Settings(
            main_llm_provider="anthropic",
            main_llm_model="custom-main-model",
            anthropic_api_key="test",
        )
    )
    assert provider._model == "custom-main-model"


def test_critic_and_judge_models_are_configured_independently():
    reviewer = build_adversarial_reviewer(
        Settings(
            reviewer_critic_provider="openai",
            reviewer_critic_model="custom-critic-model",
            reviewer_judge_provider="gemini",
            reviewer_judge_model="custom-judge-model",
        )
    )
    assert reviewer._critic._model == "custom-critic-model"
    assert reviewer._judge._model == "custom-judge-model"


async def test_gpt_5_models_use_max_completion_tokens():
    provider = OpenAICompatProvider("test", "https://api.openai.com/v1", "gpt-5.6-sol")
    provider._client.chat.completions.create = AsyncMock(
        return_value=type(
            "Response",
            (),
            {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "ok"})()})()]},
        )()
    )

    assert await provider.complete("system", "user", 123) == "ok"

    provider._client.chat.completions.create.assert_awaited_once_with(
        model="gpt-5.6-sol",
        messages=[
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        max_completion_tokens=123,
    )


async def test_openai_compatible_provider_reports_output_truncation():
    provider = OpenAICompatProvider("test", "https://api.openai.com/v1", "gpt-4o")
    provider._client.chat.completions.create = AsyncMock(
        return_value=type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "finish_reason": "length",
                            "message": type("Message", (), {"content": "partial"})(),
                        },
                    )()
                ]
            },
        )()
    )

    with pytest.raises(RuntimeError, match="truncated at the 123-token"):
        await provider.complete("system", "user", 123)


async def test_openai_compatible_provider_reports_empty_response():
    provider = OpenAICompatProvider("test", "https://api.openai.com/v1", "gpt-5.6-sol")
    provider._client.chat.completions.create = AsyncMock(
        return_value=type(
            "Response",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "finish_reason": "stop",
                            "message": type(
                                "Message", (), {"content": "", "refusal": None}
                            )(),
                        },
                    )()
                ]
            },
        )()
    )

    with pytest.raises(RuntimeError, match="empty response.*finish reason stop"):
        await provider.complete("system", "user", 123)


async def test_openai_compatible_provider_reports_missing_choices():
    provider = OpenAICompatProvider("test", "https://api.openai.com/v1", "gpt-5.6-sol")
    provider._client.chat.completions.create = AsyncMock(
        return_value=type("Response", (), {"choices": []})()
    )

    with pytest.raises(RuntimeError, match="provider returned no choices"):
        await provider.complete("system", "user", 123)


def test_evaluation_set_covers_all_diataxis_types():
    assert {case["expected"] for case in CASES} == {
        "tutorial",
        "how-to",
        "reference",
        "explanation",
    }
