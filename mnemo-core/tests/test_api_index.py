import time

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import get_indexer
from mnemo_core.config import Settings
from mnemo_core.indexing.service import Indexer
from mnemo_core.vector.sqlite_vec import SqliteVecIndex
from tests.conftest import FakeContentSource, FakeEmbedding

DOC = "---\ntitle: A\n---\n## Steps\n\nDo the thing.\n"


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


def _fake_indexer(tmp_path, documents):
    vector_index = SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=4)
    return Indexer(vector_index, FakeEmbedding(dimension=4), FakeContentSource(documents))


def test_index_trigger_embeds_requested_paths(tmp_path):
    settings = Settings(mnemo_api_token="test-secret", state_db_path=str(tmp_path / "jobs.db"))
    app = create_app(settings)
    app.dependency_overrides[get_indexer] = lambda: _fake_indexer(tmp_path, {"docs/a.md": DOC})

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/index/trigger",
            json={"commit_sha": "abc1234", "paths": ["docs/a.md"]},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert created.status_code == 202
        job = _wait_for_terminal_status(client, created.json()["id"])

    assert job["status"] == "succeeded"
    assert job["result"]["added"] == 1
    assert job["result"]["chunks"] == 1


def test_index_reconcile_prunes_and_reports_counts(tmp_path):
    settings = Settings(mnemo_api_token="test-secret", state_db_path=str(tmp_path / "jobs.db"))
    app = create_app(settings)
    app.dependency_overrides[get_indexer] = lambda: _fake_indexer(tmp_path, {"docs/a.md": DOC})

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/index/reconcile",
            json={"dry_run": False},
            headers={"Authorization": "Bearer test-secret"},
        )
        assert created.status_code == 202
        job = _wait_for_terminal_status(client, created.json()["id"])

    assert job["status"] == "succeeded"
    assert job["result"]["added"] == 1
    assert job["result"]["removed"] == 0


def test_index_reconcile_dry_run_does_not_mutate_vector_index(tmp_path):
    settings = Settings(mnemo_api_token="test-secret", state_db_path=str(tmp_path / "jobs.db"))
    app = create_app(settings)
    vector_index = SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=4)
    indexer = Indexer(vector_index, FakeEmbedding(dimension=4), FakeContentSource({"docs/a.md": DOC}))
    app.dependency_overrides[get_indexer] = lambda: indexer

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/index/reconcile",
            json={"dry_run": True},
            headers={"Authorization": "Bearer test-secret"},
        )
        job = _wait_for_terminal_status(client, created.json()["id"])

    assert job["status"] == "succeeded"
    assert vector_index.content_hashes() == {}


def test_index_endpoints_require_token(tmp_path):
    settings = Settings(mnemo_api_token="test-secret", state_db_path=str(tmp_path / "jobs.db"))
    app = create_app(settings)
    with TestClient(app) as client:
        response = client.post("/api/v1/index/trigger", json={})
    assert response.status_code == 401
