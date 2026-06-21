from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_runner
from mnemo_core.config import Settings
from tests.conftest import FakeLLM, FakePublisher, llm_json_response


def test_ingest_runs_full_pipeline(configured_settings: Settings):
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)

    app = create_app(configured_settings)
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            json={"content": "Deploy instructions here."},
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["document"]["title"] == "Deploy the app"
    assert data["publish"]["pr_url"] == "https://github.com/acme/kb/pull/1"
    assert publisher.last_doc is not None
