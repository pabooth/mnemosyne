from mnemo_curator.models import Document
from mnemo_curator.resolver import Resolver
from mnemo_curator.service import CuratorService
from mnemo_curator.settings import Settings


class FakeGitHub:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def list_documents(self) -> list[Document]:
        return [Document(path="docs/a.md", content="---\ntitle: A\n---\n\nBody")]


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
