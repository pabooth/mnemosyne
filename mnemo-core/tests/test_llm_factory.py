import pytest

from mnemo_core.config import Settings
from mnemo_core.evaluation import CASES
from mnemo_core.llm.anthropic import AnthropicProvider
from mnemo_core.llm.factory import get_provider
from mnemo_core.llm.ollama import OllamaProvider
from mnemo_core.llm.openai_compat import OpenAICompatProvider


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(llm_provider="anthropic", anthropic_api_key="test"), AnthropicProvider),
        (Settings(llm_provider="openai", openai_api_key="test"), OpenAICompatProvider),
        (Settings(llm_provider="deepseek", deepseek_api_key="test"), OpenAICompatProvider),
        (Settings(llm_provider="ollama"), OllamaProvider),
    ],
)
def test_provider_factory_contract(settings, expected):
    provider = get_provider(settings)
    assert isinstance(provider, expected)
    assert callable(provider.complete)


def test_provider_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
        get_provider(Settings(llm_provider="unknown"))


def test_evaluation_set_covers_all_diataxis_types():
    assert {case["expected"] for case in CASES} == {
        "tutorial",
        "how-to",
        "reference",
        "explanation",
    }
