import time

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner, get_runner
from mnemo_core.config import Settings
from tests.conftest import FakeLLM, FakePublisher, llm_json_response


def test_async_job_records_result(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        github_token="gh-test",
        github_repo="acme/kb",
        anthropic_api_key="test",
        state_db_path=str(tmp_path / "jobs.db"),
    )
    runner = build_runner(
        settings,
        publisher=FakePublisher(),
        llm=FakeLLM(llm_json_response()),
    )
    app = create_app(settings)
    app.dependency_overrides[get_runner] = lambda: runner

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/jobs?kind=process",
            json={"content": "Deploy instructions"},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert created.status_code == 202
        job_id = created.json()["id"]
        for _ in range(20):
            result = client.get(
                f"/api/v1/jobs/{job_id}",
                headers={"Authorization": "Bearer test-secret"},
            )
            if result.json()["status"] == "succeeded":
                break
            time.sleep(0.01)

    assert result.json()["status"] == "succeeded"
    assert result.json()["result"]["title"] == "Deploy the app"


def test_named_submitter_cannot_read_admin_audit(tmp_path):
    settings = Settings(
        mnemo_api_tokens="alice:alice-secret:submitter",
        state_db_path=str(tmp_path / "jobs.db"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/audit",
            headers={"Authorization": "Bearer alice-secret"},
        )
    assert response.status_code == 403
