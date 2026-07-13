from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_publisher, get_reviewer, get_runner
from mnemo_core.config import Settings
from mnemo_core.models import AdversarialReviewResult
from tests.conftest import FakeLLM, FakePublisher, llm_json_response, processed_doc


def test_publish_uses_reviewed_document_without_llm(configured_settings: Settings):
    llm = FakeLLM(llm_json_response(title="LLM title should not be used"))
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)
    app = create_app(configured_settings)
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/publish",
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
            "/api/v1/publish",
            json=payload,
            headers={"Authorization": "Bearer test-secret"},
        )
    assert response.status_code == 422


def test_publish_reviewer_dependency_attaches_success(configured_settings: Settings):
    class AcceptingReviewer:
        async def review(self, doc, published):
            return AdversarialReviewResult(
                tier="tier-1",
                outcome="accepted",
                requires_human_review=False,
                merged=True,
                reason="Both accepted.",
            )

    app = create_app(configured_settings)
    app.dependency_overrides[get_publisher] = lambda: FakePublisher()
    app.dependency_overrides[get_reviewer] = lambda: AcceptingReviewer()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/publish",
            json=processed_doc().model_dump(),
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    assert response.json()["review"]["outcome"] == "accepted"
    assert response.json()["review"]["merged"] is True


def test_publish_reviewer_dependency_attaches_escalation(configured_settings: Settings):
    class EscalatingReviewer:
        async def review(self, doc, published):
            return AdversarialReviewResult(
                tier="tier-1",
                outcome="escalated",
                requires_human_review=True,
                reason="Reviewer unavailable.",
            )

    app = create_app(configured_settings)
    app.dependency_overrides[get_publisher] = lambda: FakePublisher()
    app.dependency_overrides[get_reviewer] = lambda: EscalatingReviewer()

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/publish",
            json=processed_doc().model_dump(),
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    assert response.json()["review"]["outcome"] == "escalated"
    assert response.json()["review"]["requires_human_review"] is True
