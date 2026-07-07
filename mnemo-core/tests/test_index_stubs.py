import time

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.config import Settings


def _wait_for_terminal_status(client: TestClient, job_id: str) -> dict:
    for _ in range(50):
        job = client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"Authorization": "Bearer test-secret"},
        ).json()
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.01)
    return job


def test_index_trigger_stub_fails_immediately_without_retry(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        state_db_path=str(tmp_path / "jobs.db"),
        job_max_attempts=3,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/index/trigger",
            json={"commit_sha": "abc1234", "paths": ["docs/how-to/deploy.md"]},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert created.status_code == 202
        job = _wait_for_terminal_status(client, created.json()["id"])

    assert job["status"] == "failed"
    assert job["attempts"] == 1
    assert "stub" in job["error"]


def test_index_reconcile_stub_accepts_empty_body(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        state_db_path=str(tmp_path / "jobs.db"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/index/reconcile",
            json={"dry_run": True},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert created.status_code == 202
        job = _wait_for_terminal_status(client, created.json()["id"])

    assert job["status"] == "failed"
    assert job["attempts"] == 1


def test_index_endpoints_require_token(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        state_db_path=str(tmp_path / "jobs.db"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post("/api/v1/index/trigger", json={})
    assert response.status_code == 401
