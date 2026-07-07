import posixpath
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import PurePosixPath

from .frontmatter import parse_frontmatter
from .models import Document, Finding
from .settings import Settings

LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)#]+)")
TODO_RE = re.compile(r"\b(TODO|TBD|FIXME)\b", re.IGNORECASE)
EMPTY_SECTION_RE = re.compile(r"^#{2,6}\s+.+\n\s*(?=#{1,6}\s|\Z)", re.MULTILINE)


class Inspector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def inspect(self, documents: list[Document]) -> list[Finding]:
        findings: list[Finding] = []
        titles: Counter[str] = Counter()
        title_paths: dict[str, list[str]] = {}
        known_paths = {document.path for document in documents}
        stale_before = date.today() - timedelta(days=self.settings.curator_stale_after_days)

        for document in documents:
            metadata = parse_frontmatter(document.content)
            title = metadata.get("title", "").strip().lower()
            if title:
                titles[title] += 1
                title_paths.setdefault(title, []).append(document.path)

            findings.extend(self._structural_findings(document, metadata, known_paths, stale_before))
            findings.extend(self._semantic_findings(document))

        for title, count in titles.items():
            if count > 1:
                findings.append(
                    Finding(
                        kind="duplicate-title",
                        severity="medium",
                        title=title,
                        detail=f"{count} documents share the title '{title}'",
                        metadata={"count": count, "paths": ", ".join(title_paths[title])},
                    )
                )

        return findings

    def _structural_findings(
        self,
        document: Document,
        metadata: dict[str, str],
        known_paths: set[str],
        stale_before: date,
    ) -> list[Finding]:
        findings: list[Finding] = []
        if not metadata.get("owner"):
            findings.append(
                Finding(
                    kind="missing-owner",
                    severity="medium",
                    path=document.path,
                    detail="Document frontmatter does not define an owner",
                )
            )

        reviewed = metadata.get("last_reviewed", "")
        if reviewed:
            try:
                if date.fromisoformat(reviewed) < stale_before:
                    findings.append(
                        Finding(
                            kind="stale",
                            severity="low",
                            path=document.path,
                            detail="Document review date is older than the configured threshold",
                            metadata={"last_reviewed": reviewed},
                        )
                    )
            except ValueError:
                findings.append(
                    Finding(
                        kind="invalid-review-date",
                        severity="medium",
                        path=document.path,
                        detail="Document last_reviewed value is not an ISO date",
                        metadata={"value": reviewed},
                    )
                )

        for target in LINK_RE.findall(document.content):
            resolved = self._resolve_link_target(document.path, target)
            if resolved not in known_paths:
                findings.append(
                    Finding(
                        kind="broken-relative-link",
                        severity="high",
                        path=document.path,
                        detail="Document links to a relative path that was not found",
                        metadata={"target": target},
                    )
                )

        return findings

    def _resolve_link_target(self, document_path: str, target: str) -> str:
        if target.startswith("/"):
            root = self.settings.docs_root.strip("/")
            base = f"{root}/{target.lstrip('/')}" if root else target.lstrip("/")
            return posixpath.normpath(base)
        return posixpath.normpath(str(PurePosixPath(document_path).parent.joinpath(target)))

    def _semantic_findings(self, document: Document) -> list[Finding]:
        findings: list[Finding] = []
        if TODO_RE.search(document.content):
            findings.append(
                Finding(
                    kind="semantic-gap",
                    severity="medium",
                    path=document.path,
                    detail="Document contains TODO/TBD/FIXME placeholder text",
                    metadata={"reason": "placeholder"},
                )
            )
        if EMPTY_SECTION_RE.search(document.content):
            findings.append(
                Finding(
                    kind="semantic-gap",
                    severity="low",
                    path=document.path,
                    detail="Document contains a heading with no body content",
                    metadata={"reason": "empty-section"},
                )
            )
        return findings
