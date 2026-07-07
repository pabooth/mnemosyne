from typing import Protocol

from .frontmatter import set_frontmatter_value, set_reviewed_today
from .models import Document, Finding, Resolution
from .semantic import SemanticResolver
from .settings import Settings


class Submitter(Protocol):
    async def submit(self, document: Document) -> str: ...


class Resolver:
    def __init__(
        self,
        settings: Settings,
        submitter: Submitter,
        semantic_resolver: SemanticResolver | None = None,
    ) -> None:
        self.settings = settings
        self.submitter = submitter
        self.semantic_resolver = semantic_resolver or SemanticResolver(settings)

    async def resolve(self, document: Document | None, finding: Finding) -> Resolution:
        if document is None:
            return Resolution(finding=finding, status="skipped", reason="Finding is not tied to a single document")

        try:
            corrected = await self._correct(document, finding)
            if corrected is None:
                return Resolution(finding=finding, status="skipped", reason="No safe automatic fix is available")
            job_id = await self.submitter.submit(Document(path=document.path, content=corrected))
            return Resolution(
                finding=finding,
                status="submitted",
                submitted_job_id=job_id,
                corrected_content=corrected,
            )
        except Exception as error:
            return Resolution(finding=finding, status="failed", reason=str(error)[:2_000])

    async def _correct(self, document: Document, finding: Finding) -> str | None:
        if finding.kind == "missing-owner":
            return set_frontmatter_value(document.content, "owner", self.settings.curator_default_owner)
        if finding.kind in {"stale", "invalid-review-date"}:
            return set_reviewed_today(document.content)
        if finding.kind == "semantic-gap":
            if not self.settings.curator_semantic_resolution_enabled:
                return None
            return await self.semantic_resolver.rewrite(document.content, finding)
        return None
