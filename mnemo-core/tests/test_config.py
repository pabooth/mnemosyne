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
