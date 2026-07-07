from .core_client import MnemoCoreClient
from .github import GitHubClient
from .inspector import Inspector
from .issue_trackers import IssueTracker, build_issue_tracker
from .models import CuratorReport, Document, Finding, Resolution
from .resolver import Resolver
from .settings import Settings


class CuratorService:
    def __init__(
        self,
        settings: Settings,
        github: GitHubClient | None = None,
        issue_tracker: IssueTracker | None = None,
        resolver: Resolver | None = None,
    ) -> None:
        self.settings = settings
        self.github = github or GitHubClient(settings)
        self.issue_tracker = issue_tracker or build_issue_tracker(settings)
        self.inspector = Inspector(settings)
        self.resolver = resolver or Resolver(settings, MnemoCoreClient(settings))

    async def scan(self, resolve: bool = False) -> CuratorReport:
        documents = await self.github.list_documents()
        findings = self.inspector.inspect(documents)
        recorded = [await self._record_issue(finding) for finding in findings]
        resolutions: list[Resolution] = []
        if resolve:
            by_path = {document.path: document for document in documents}
            resolutions = [await self._resolve_finding(by_path, finding) for finding in recorded]
        return CuratorReport(
            repository=self.settings.github_repo,
            documents_scanned=len(documents),
            findings=recorded,
            resolutions=resolutions,
        )

    async def _record_issue(self, finding: Finding) -> Finding:
        issue_url = await self.issue_tracker.record(finding)
        return finding.model_copy(update={"issue_url": issue_url})

    async def _resolve_finding(self, by_path: dict[str, Document], finding: Finding) -> Resolution:
        document = by_path.get(finding.path) if finding.path else None
        return await self.resolver.resolve(document, finding)
