import json

import pytest

from mnemo_core.config import Settings, configure_settings
from mnemo_core.embeddings.base import EmbeddingProvider
from mnemo_core.llm.base import LLMProvider
from mnemo_core.models import DocumentInput, ProcessedDocument, PublishResult
from mnemo_core.pipeline.publish import Publisher
from mnemo_core.pipeline.templates import Template, TemplateSet, configure_template_set

SAMPLE_TEMPLATES = TemplateSet(
    [
        Template(
            type="reference",
            sub_label="standard",
            description="Rules the organisation mandates, with RFC 2119 language.",
            body="## Introduction\n\n## Policies\n\n## Review",
            tier="tier-2",
        ),
        Template(
            type="how-to",
            sub_label="procedure",
            description="Step-by-step instructions for an operational task.",
            body="## Goal\n\n## Steps\n\n## Verification",
            tier="tier-1",
        ),
    ]
)

VALID_PROCESSED_JSON = {
    "title": "Deploy the app",
    "type": "how-to",
    "review_tier": "tier-1",
    "sub_label": "procedure",
    "status": "draft",
    "tags": ["deploy", "ops"],
    "summary": "Steps to deploy the application.",
    "owner": "platform",
    "last_reviewed": "2026-06-14",
    "flags": [],
    "body": "## Steps\n\n1. Build\n2. Ship",
    "acceptance_case": {
        "claims": ["The procedure states a bounded task."],
        "evidence": ["It provides verifiable steps."],
        "diataxis_fit": "It is a task-oriented how-to.",
        "anticipated_objections": [],
        "limitations": [],
        "pipeline_pending": [],
    },
}


@pytest.fixture(autouse=True)
def reset_settings():
    configure_settings(None)
    # ADR-018: templates are fetched from GitHub on first use; tests must
    # never reach the network, so pin a sample set for every test.
    configure_template_set(SAMPLE_TEMPLATES)
    yield
    configure_settings(None)
    configure_template_set(None)


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        mnemo_api_token="test-secret",
        github_token="gh-test",
        github_repo="acme/kb",
        main_llm_provider="anthropic",
        state_db_path=str(tmp_path / "state.db"),
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
        self.last_max_tokens: int | None = None
        self.calls: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        self.last_system = system
        self.last_user = user
        self.last_max_tokens = max_tokens
        self.calls.append((system, user))
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


class FakeEmbedding(EmbeddingProvider):
    def __init__(self, dimension: int = 4) -> None:
        self.dimension = dimension
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(i)] + [0.0] * (self.dimension - 1) for i in range(len(texts))]


class FakeContentSource:
    def __init__(self, documents: dict[str, str]) -> None:
        self.documents = documents
        self.fetched_refs: list[str] = []

    async def fetch(self, path: str, ref: str = "") -> str:
        self.fetched_refs.append(ref)
        return self.documents[path]

    async def list_documents(self) -> list[tuple[str, str]]:
        return list(self.documents.items())


def processed_doc(**overrides) -> ProcessedDocument:
    data = {**VALID_PROCESSED_JSON, **overrides}
    return ProcessedDocument(**data)


def sample_input(**overrides) -> DocumentInput:
    defaults = {"content": "Deploy instructions here."}
    defaults.update(overrides)
    return DocumentInput(**defaults)


def llm_json_response(**overrides) -> str:
    return json.dumps({**VALID_PROCESSED_JSON, **overrides})
