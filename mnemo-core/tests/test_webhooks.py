import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.config import Settings


def test_webhook_requires_valid_signature(tmp_path):
    settings = Settings(
        github_webhook_secret="secret",
        state_db_path=str(tmp_path / "state.db"),
    )
    app = create_app(settings)
    body = json.dumps({"ref": "refs/heads/main"}).encode()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": "sha256=wrong",
            },
        )
    assert response.status_code == 401


def test_webhook_ignores_unwatched_branch(tmp_path):
    settings = Settings(
        github_webhook_secret="secret",
        github_webhook_branch="main",
        state_db_path=str(tmp_path / "state.db"),
    )
    app = create_app(settings)
    body = json.dumps({"ref": "refs/heads/other"}).encode()
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": signature,
            },
        )
    assert response.status_code == 202
    assert response.json()["accepted"] is False
