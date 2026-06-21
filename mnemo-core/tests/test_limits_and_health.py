from importlib.metadata import version

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_runner
from mnemo_core.config import Settings
from tests.conftest import FakeLLM, FakePublisher, llm_json_response


def test_readiness_reports_missing_configuration(tmp_path):
    app = create_app(Settings(state_db_path=str(tmp_path / "state.db")))
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["api_token"] is False


def test_rate_limit_is_enforced(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        anthropic_api_key="test",
        github_token="gh-test",
        github_repo="acme/kb",
        request_rate_limit_per_minute=1,
        state_db_path=str(tmp_path / "state.db"),
    )
    runner = build_runner(
        settings,
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
    )
    app = create_app(settings)
    app.dependency_overrides[get_runner] = lambda: runner
    headers = {"Authorization": "Bearer test-secret"}

    with TestClient(app) as client:
        first = client.post("/api/process", json={"content": "hello"}, headers=headers)
        second = client.post("/api/process", json={"content": "hello"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 429


def test_api_version_matches_package_metadata(tmp_path):
    app = create_app(Settings(state_db_path=str(tmp_path / "state.db")))
    assert app.version == version("mnemo-core")
