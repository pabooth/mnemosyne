import pytest
from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_runner
from mnemo_core.config import Settings, configure_settings
from tests.conftest import FakeLLM, FakePublisher, llm_json_response


@pytest.fixture
def client(configured_settings: Settings):
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)

    app = create_app(configured_settings)
    app.dependency_overrides[get_runner] = lambda: runner
    with TestClient(app) as test_client:
        yield test_client, publisher
    app.dependency_overrides.clear()
    configure_settings(None)


def test_health_unauthenticated(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_requires_auth(client):
    test_client, _ = client
    response = test_client.post("/api/process", json={"content": "hello"})
    assert response.status_code == 401


def test_process_returns_processed_document(client):
    test_client, publisher = client
    response = test_client.post(
        "/api/process",
        json={"content": "Deploy instructions here."},
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Deploy the app"
    assert data["type"] == "how-to"
    assert publisher.last_doc is None


def test_process_pipeline_error_returns_502(configured_settings: Settings):
    llm = FakeLLM("bad")
    runner = build_runner(configured_settings, publisher=FakePublisher(), llm=llm)
    app = create_app(configured_settings)
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/process",
            json={"content": "hello"},
            headers={"Authorization": "Bearer test-secret"},
        )
    assert response.status_code == 502


def test_process_returns_503_when_auth_not_configured():
    app = create_app(Settings(mnemo_api_token=""))
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/process",
            json={"content": "hello"},
            headers={"Authorization": "Bearer anything"},
        )
    assert response.status_code == 503
