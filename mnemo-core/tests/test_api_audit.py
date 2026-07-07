from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.config import Settings


def test_admin_audit_response_uses_typed_contract(tmp_path):
    settings = Settings(
        mnemo_api_token="test-secret",
        state_db_path=str(tmp_path / "jobs.db"),
    )
    app = create_app(settings)
    app.state.job_store.record_audit(
        actor="alice",
        action="POST /api/v1/jobs",
        status=202,
        details={"query": "kind=ingest"},
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/audit",
            headers={"Authorization": "Bearer test-secret"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "actor": "alice",
            "action": "POST /api/v1/jobs",
            "status": 202,
            "details": {"query": "kind=ingest"},
            "created_at": response.json()[0]["created_at"],
        }
    ]
    schema = app.openapi()["paths"]["/api/v1/audit"]["get"]["responses"]["200"]
    assert schema["content"]["application/json"]["schema"]["items"]["$ref"] == (
        "#/components/schemas/AuditEntry"
    )
