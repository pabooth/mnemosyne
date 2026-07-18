import pytest
from pydantic import ValidationError

from mnemo_core.config import Settings


def test_db_paths_default_to_component_subdirectory(monkeypatch):
    monkeypatch.delenv("STATE_DB_PATH", raising=False)
    monkeypatch.delenv("VECTOR_DB_PATH", raising=False)
    settings = Settings(_env_file=None)
    assert settings.state_db_path == "./data/mnemo-core/state.db"
    assert settings.vector_db_path == "./data/mnemo-core/vectors.db"


def test_explicit_db_paths_override_defaults(monkeypatch):
    settings = Settings(
        _env_file=None,
        state_db_path="/data/state.db",
        vector_db_path="/data/vectors.db",
    )
    assert settings.state_db_path == "/data/state.db"
    assert settings.vector_db_path == "/data/vectors.db"


def test_explicit_empty_vector_db_path_opts_in_to_sharing():
    settings = Settings(_env_file=None, vector_db_path="")
    assert settings.vector_db_path == ""


@pytest.mark.parametrize(
    ("main", "critic", "judge"),
    [
        ("openai", "OPENAI", "gemini"),
        ("anthropic", "openai", "OPENAI"),
        ("Gemini", "openai", "gemini"),
    ],
)
def test_adjudication_provider_families_must_differ(main, critic, judge):
    with pytest.raises(ValidationError, match="different families"):
        Settings(
            _env_file=None,
            adversarial_review_enabled=True,
            main_llm_provider=main,
            reviewer_critic_provider=critic,
            reviewer_judge_provider=judge,
        )


def test_adjudication_provider_families_are_normalized():
    settings = Settings(
        _env_file=None,
        main_llm_provider=" Anthropic ",
        reviewer_critic_provider=" OPENAI ",
        reviewer_judge_provider="GEMINI",
    )
    assert settings.main_llm_provider == "anthropic"
    assert settings.reviewer_critic_provider == "openai"
    assert settings.reviewer_judge_provider == "gemini"


def test_same_adjudication_family_is_allowed_when_review_is_disabled():
    settings = Settings(
        _env_file=None,
        adversarial_review_enabled=False,
        main_llm_provider="openai",
        reviewer_critic_provider="OPENAI",
        reviewer_judge_provider="openai",
    )
    assert settings.main_llm_provider == "openai"
    assert settings.reviewer_critic_provider == "openai"
    assert settings.reviewer_judge_provider == "openai"


def test_adversarial_review_is_disabled_by_default():
    assert Settings(_env_file=None).adversarial_review_enabled is False


def test_xai_and_gemini_defaults():
    settings = Settings(_env_file=None)
    assert settings.xai_base_url == "https://api.x.ai/v1"
    assert settings.gemini_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_llm_slots_have_independent_model_defaults():
    settings = Settings(_env_file=None)
    assert settings.main_llm_provider == "anthropic"
    assert settings.main_llm_model == "claude-sonnet-4-6"
    assert settings.reviewer_critic_model == "gpt-4o"
    assert settings.reviewer_judge_model == "gemini-2.5-pro"
