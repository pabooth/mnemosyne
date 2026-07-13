from mnemo_curator.settings import Settings


def test_issue_db_path_defaults_to_component_subdirectory(monkeypatch):
    monkeypatch.delenv("CURATOR_ISSUE_DB_PATH", raising=False)
    settings = Settings(_env_file=None)
    assert settings.curator_issue_db_path == "./data/mnemo-curator/issues.db"


def test_explicit_issue_db_path_overrides_default():
    settings = Settings(_env_file=None, curator_issue_db_path="/data/issues.db")
    assert settings.curator_issue_db_path == "/data/issues.db"
