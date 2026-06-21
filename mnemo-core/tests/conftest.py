import json

import pytest

from mnemo_core.config import Settings, configure_settings
from mnemo_core.llm.base import LLMProvider
from mnemo_core.models import DocumentInput, ProcessedDocument, PublishResult
from mnemo_core.pipeline.publish import Publisher

VALID_PROCESSED_JSON = {
    "title": "Deploy the app",
    "type": "how-to",
    "sub_label": "procedure",
    "status": "draft",
    "tags": ["deploy", "ops"],
    "summary": "Steps to deploy the application.",
    "owner": "platform",
    "last_reviewed": "2026-06-14",
    "flags": [],
    "body": "## Steps\n\n1. Build\n2. Ship",
}


@pytest.fixture(autouse=True)
def reset_settings():
    configure_settings(None)
    yield
    configure_settings(None)


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        mnemo_api_token="test-secret",
        github_token="gh-test",
        github_repo="acme/kb",
        llm_provider="anthropic",
    )


@pytest.fixture
def configured_settings(test_settings: Settings):
    configure_settings(test_settings)
    return test_settings


class FakeLLM(LLMProvider):
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_system: str | None = None
        self.last_user: str | None = None

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        self.last_system = system
        self.last_user = user
        return self.response


class FakePublisher(Publisher):
    def __init__(self, result: PublishResult | None = None) -> None:
        self.last_doc: ProcessedDocument | None = None
        self.result = result or PublishResult(
            pr_url="https://github.com/acme/kb/pull/1",
            branch="mnemo/how-to/deploy-the-app-2026-06-14-test",
            file_path="how-to/deploy-the-app.md",
        )

    async def publish(self, doc: ProcessedDocument) -> PublishResult:
        self.last_doc = doc
        return self.result


def processed_doc(**overrides) -> ProcessedDocument:
    data = {**VALID_PROCESSED_JSON, **overrides}
    return ProcessedDocument(**data)


def sample_input(**overrides) -> DocumentInput:
    defaults = {"content": "Deploy instructions here."}
    defaults.update(overrides)
    return DocumentInput(**defaults)


def llm_json_response(**overrides) -> str:
    return json.dumps({**VALID_PROCESSED_JSON, **overrides})
