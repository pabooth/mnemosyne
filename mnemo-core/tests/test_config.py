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


def test_reviewer_provider_families_must_differ():
    with pytest.raises(ValidationError, match="different families"):
        Settings(
            _env_file=None,
            reviewer_advocate_provider="openai",
            reviewer_critic_provider="OPENAI",
        )


def test_reviewer_provider_families_are_normalized():
    settings = Settings(
        _env_file=None,
        reviewer_advocate_provider=" Anthropic ",
        reviewer_critic_provider="GEMINI",
    )
    assert settings.reviewer_advocate_provider == "anthropic"
    assert settings.reviewer_critic_provider == "gemini"


def test_same_reviewer_family_is_allowed_when_review_is_disabled():
    settings = Settings(
        _env_file=None,
        adversarial_review_enabled=False,
        reviewer_advocate_provider="openai",
        reviewer_critic_provider="OPENAI",
    )
    assert settings.reviewer_advocate_provider == "openai"
    assert settings.reviewer_critic_provider == "openai"


def test_xai_and_gemini_defaults():
    settings = Settings(_env_file=None)
    assert settings.xai_base_url == "https://api.x.ai/v1"
    assert settings.xai_model == "grok-4.5"
    assert settings.gemini_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert settings.gemini_model == "gemini-3.5-flash"
