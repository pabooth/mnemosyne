from mnemo_curator.models import Document, Resolution
from mnemo_curator.resolver import Resolver
from mnemo_curator.service import CuratorService
from mnemo_curator.settings import Settings


class FakeGitHub:
    def __init__(self, documents: list[Document] | None = None) -> None:
        self.events: list[str] = []
        self.documents = documents or [Document(path="docs/a.md", content="---\ntitle: A\n---\n\nBody")]

    async def list_documents(self) -> list[Document]:
        return self.documents


class FakeIssueTracker:
    def __init__(self, github: FakeGitHub) -> None:
        self.github = github

    async def record(self, finding):
        self.github.events.append(f"issue:{finding.kind}")
        return "https://example.test/issues/1"


class OrderedSubmitter:
    def __init__(self, github: FakeGitHub) -> None:
        self.github = github

    async def submit(self, document: Document) -> str:
        self.github.events.append("submit")
        return "job-1"


class FlakyIssueTracker:
    async def record(self, finding):
        if finding.path == "docs/a.md":
            raise RuntimeError("issue tracker unavailable")
        return "https://example.test/issues/2"


class FlakyResolver:
    async def resolve(self, document, finding):
        if finding.path == "docs/a.md":
            raise RuntimeError("resolver exploded")
        return Resolution(finding=finding, status="skipped", reason="no fix")


async def test_service_records_issue_before_resolving():
    github = FakeGitHub()
    settings = Settings(curator_default_owner="platform")
    resolver = Resolver(settings, OrderedSubmitter(github))
    issue_tracker = FakeIssueTracker(github)
    service = CuratorService(
        settings,
        github=github,  # type: ignore[arg-type]
        issue_tracker=issue_tracker,
        resolver=resolver,
    )

    report = await service.scan(resolve=True)

    assert report.findings[0].issue_url == "https://example.test/issues/1"
    assert github.events == ["issue:missing-owner", "submit"]


async def test_service_tolerates_issue_recording_failure():
    documents = [
        Document(path="docs/a.md", content="Body"),
        Document(path="docs/b.md", content="Body"),
    ]
    github = FakeGitHub(documents)
    settings = Settings()
    service = CuratorService(
        settings,
        github=github,  # type: ignore[arg-type]
        issue_tracker=FlakyIssueTracker(),
        resolver=Resolver(settings, OrderedSubmitter(github)),
    )

    report = await service.scan()

    paths = {finding.path: finding.issue_url for finding in report.findings}
    assert paths == {
        "docs/a.md": "",
        "docs/b.md": "https://example.test/issues/2",
    }


async def test_service_tolerates_resolution_failure():
    documents = [
        Document(path="docs/a.md", content="Body"),
        Document(path="docs/b.md", content="Body"),
    ]
    github = FakeGitHub(documents)
    settings = Settings()
    service = CuratorService(
        settings,
        github=github,  # type: ignore[arg-type]
        issue_tracker=FakeIssueTracker(github),
        resolver=FlakyResolver(),  # type: ignore[arg-type]
    )

    report = await service.scan(resolve=True)

    statuses = {resolution.finding.path: resolution.status for resolution in report.resolutions}
    assert statuses == {"docs/a.md": "failed", "docs/b.md": "skipped"}
