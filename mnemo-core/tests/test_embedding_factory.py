import pytest

from mnemo_core.config import Settings
from mnemo_core.embeddings.factory import get_embedding_provider
from mnemo_core.embeddings.ollama import OllamaEmbedding
from mnemo_core.embeddings.openai_compat import OpenAICompatEmbedding


@pytest.mark.parametrize(
    ("settings", "expected"),
    [
        (Settings(embedding_provider="openai", openai_api_key="test"), OpenAICompatEmbedding),
        (Settings(embedding_provider="ollama"), OllamaEmbedding),
    ],
)
def test_embedding_factory_contract(settings, expected):
    provider = get_embedding_provider(settings)
    assert isinstance(provider, expected)
    assert callable(provider.embed)


def test_embedding_factory_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown EMBEDDING_PROVIDER"):
        get_embedding_provider(Settings(embedding_provider="unknown"))
