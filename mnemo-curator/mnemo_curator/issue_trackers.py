import json
import sqlite3
from pathlib import Path
from typing import Literal, Protocol

import httpx

from .models import Finding
from .settings import Settings

IssueTrackerKind = Literal["github", "jira", "sqlite"]


class IssueTracker(Protocol):
    async def record(self, finding: Finding) -> str: ...


def build_issue_tracker(settings: Settings) -> IssueTracker:
    if settings.curator_issue_tracker == "github":
        return GitHubIssueTracker(settings)
    if settings.curator_issue_tracker == "jira":
        return JiraIssueTracker(settings)
    if settings.curator_issue_tracker == "sqlite":
        return SQLiteIssueTracker(settings)
    raise ValueError(f"Unsupported issue tracker: {settings.curator_issue_tracker}")


class GitHubIssueTracker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def record(self, finding: Finding) -> str:
        if not self.settings.github_token or not self.settings.github_repo:
            raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO are required for GitHub issue tracking")
        async with httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {self.settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        ) as client:
            response = await client.post(
                f"/repos/{self.settings.github_repo}/issues",
                json={
                    "title": issue_title(finding),
                    "body": issue_body(finding),
                    "labels": self.settings.issue_labels,
                },
            )
            response.raise_for_status()
        return str(response.json().get("html_url", ""))


class JiraIssueTracker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def record(self, finding: Finding) -> str:
        if not self.settings.jira_base_url or not self.settings.jira_project_key:
            raise RuntimeError("JIRA_BASE_URL and JIRA_PROJECT_KEY are required for Jira issue tracking")
        if not self.settings.jira_email or not self.settings.jira_api_token:
            raise RuntimeError("JIRA_EMAIL and JIRA_API_TOKEN are required for Jira issue tracking")

        async with httpx.AsyncClient(
            base_url=self.settings.jira_base_url.rstrip("/"),
            auth=(self.settings.jira_email, self.settings.jira_api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30,
        ) as client:
            response = await client.post(
                "/rest/api/3/issue",
                json={
                    "fields": {
                        "project": {"key": self.settings.jira_project_key},
                        "issuetype": {"name": self.settings.jira_issue_type},
                        "summary": issue_title(finding),
                        "description": jira_description(finding),
                        "labels": self.settings.issue_labels,
                    }
                },
            )
            response.raise_for_status()
        key = str(response.json().get("key", ""))
        return f"{self.settings.jira_base_url.rstrip('/').removesuffix('/browse')}/browse/{key}" if key else ""


class SQLiteIssueTracker:
    def __init__(self, settings: Settings) -> None:
        self.path = settings.curator_issue_db_path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    async def record(self, finding: Finding) -> str:
        db = self._connect()
        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO curator_issues "
                    "(kind, severity, path, title, detail, metadata_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                    (
                        finding.kind,
                        finding.severity,
                        finding.path,
                        finding.title,
                        finding.detail,
                        json.dumps(finding.metadata, sort_keys=True),
                    ),
                )
                issue_id = cursor.lastrowid
        finally:
            db.close()
        return f"sqlite://{self.path}#curator_issues/{issue_id}"

    def _initialize(self) -> None:
        db = self._connect()
        try:
            with db:
                db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS curator_issues (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kind TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        path TEXT NOT NULL,
                        title TEXT NOT NULL,
                        detail TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
        finally:
            db.close()


def issue_title(finding: Finding) -> str:
    title = f"mnemo-curator: {finding.kind}"
    if finding.path:
        title = f"{title} in {finding.path}"
    elif finding.title:
        title = f"{title}: {finding.title}"
    return title


def issue_body(finding: Finding) -> str:
    details = [f"**Kind:** {finding.kind}", f"**Severity:** {finding.severity}"]
    if finding.path:
        details.append(f"**Path:** `{finding.path}`")
    if finding.title:
        details.append(f"**Title:** {finding.title}")
    if finding.detail:
        details.append(f"**Detail:** {finding.detail}")
    if finding.metadata:
        details.append("**Metadata:**")
        details.extend(f"- `{key}`: `{value}`" for key, value in finding.metadata.items())
    return "\n\n".join(details)


def jira_description(finding: Finding) -> dict:
    paragraphs = [
        f"Kind: {finding.kind}",
        f"Severity: {finding.severity}",
    ]
    if finding.path:
        paragraphs.append(f"Path: {finding.path}")
    if finding.title:
        paragraphs.append(f"Title: {finding.title}")
    if finding.detail:
        paragraphs.append(f"Detail: {finding.detail}")
    if finding.metadata:
        metadata = ", ".join(f"{key}={value}" for key, value in finding.metadata.items())
        paragraphs.append(f"Metadata: {metadata}")

    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": paragraph}],
            }
            for paragraph in paragraphs
        ],
    }
