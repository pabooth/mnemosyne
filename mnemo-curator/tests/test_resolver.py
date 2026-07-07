from mnemo_curator.models import Document, Finding
from mnemo_curator.resolver import Resolver
from mnemo_curator.settings import Settings


class FakeSubmitter:
    def __init__(self) -> None:
        self.submitted: list[Document] = []

    async def submit(self, document: Document) -> str:
        self.submitted.append(document)
        return "job-1"


class FakeSemanticResolver:
    async def rewrite(self, content: str, finding: Finding) -> str:
        return content.replace("TODO", "Documented behavior.")


async def test_resolver_submits_missing_owner_fix():
    submitter = FakeSubmitter()
    resolver = Resolver(Settings(curator_default_owner="platform"), submitter)
    document = Document(path="docs/a.md", content="---\ntitle: A\n---\n\nBody")

    result = await resolver.resolve(document, Finding(kind="missing-owner", path="docs/a.md"))

    assert result.status == "submitted"
    assert "owner: platform" in submitter.submitted[0].content


async def test_resolver_skips_semantic_fix_when_disabled():
    resolver = Resolver(Settings(curator_semantic_resolution_enabled=False), FakeSubmitter())
    document = Document(path="docs/a.md", content="TODO")

    result = await resolver.resolve(document, Finding(kind="semantic-gap", path="docs/a.md"))

    assert result.status == "skipped"


async def test_resolver_uses_semantic_resolver_when_enabled():
    submitter = FakeSubmitter()
    resolver = Resolver(
        Settings(curator_semantic_resolution_enabled=True),
        submitter,
        semantic_resolver=FakeSemanticResolver(),  # type: ignore[arg-type]
    )
    document = Document(path="docs/a.md", content="TODO")

    result = await resolver.resolve(document, Finding(kind="semantic-gap", path="docs/a.md"))

    assert result.status == "submitted"
    assert submitter.submitted[0].content == "Documented behavior."
