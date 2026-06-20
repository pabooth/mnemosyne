from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_runner
from mnemo_core.config import Settings
from tests.conftest import FakeLLM, FakePublisher, llm_json_response, processed_doc


def test_publish_uses_reviewed_document_without_llm(configured_settings: Settings):
    llm = FakeLLM(llm_json_response(title="LLM title should not be used"))
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)
    app = create_app(configured_settings)
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as client:
        response = client.post(
            "/api/publish",
            json=processed_doc(title="Human reviewed title").model_dump(),
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    assert publisher.last_doc is not None
    assert publisher.last_doc.title == "Human reviewed title"
    assert llm.last_user is None


def test_publish_rejects_invalid_type(configured_settings: Settings):
    app = create_app(configured_settings)
    payload = processed_doc().model_dump()
    payload["type"] = "invalid"
    with TestClient(app) as client:
        response = client.post(
            "/api/publish",
            json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
    assert response.status_code == 422
