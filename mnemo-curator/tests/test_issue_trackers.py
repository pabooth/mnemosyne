import sqlite3

import respx
from httpx import Response

from mnemo_curator.issue_trackers import (
    GitHubIssueTracker,
    JiraIssueTracker,
    SQLiteIssueTracker,
    build_issue_tracker,
)
from mnemo_curator.models import Finding
from mnemo_curator.settings import Settings


async def test_github_issue_tracker_creates_issue():
    settings = Settings(
        github_token="token",
        github_repo="owner/repo",
        curator_issue_labels="mnemo-curator,docs",
    )

    with respx.mock:
        route = respx.post("https://api.github.com/repos/owner/repo/issues").mock(
            return_value=Response(201, json={"html_url": "https://github.test/issue/1"})
        )
        issue_url = await GitHubIssueTracker(settings).record(
            Finding(kind="missing-owner", path="docs/a.md", detail="Missing owner")
        )

    assert issue_url == "https://github.test/issue/1"
    assert route.calls.last.request.headers["authorization"] == "Bearer token"
    assert route.calls.last.request.content


async def test_jira_issue_tracker_creates_issue():
    settings = Settings(
        curator_issue_tracker="jira",
        jira_base_url="https://jira.example.test",
        jira_email="docs@example.test",
        jira_api_token="secret",
        jira_project_key="DOC",
        jira_issue_type="Bug",
    )
    with respx.mock:
        route = respx.post("https://jira.example.test/rest/api/3/issue").mock(
            return_value=Response(201, json={"key": "DOC-123"})
        )
        issue_url = await JiraIssueTracker(settings).record(
            Finding(kind="semantic-gap", path="docs/a.md", detail="Placeholder")
        )

    assert issue_url == "https://jira.example.test/browse/DOC-123"
    assert route.calls.last.request.content


async def test_sqlite_issue_tracker_records_finding(tmp_path):
    db_path = tmp_path / "issues.db"
    settings = Settings(curator_issue_tracker="sqlite", curator_issue_db_path=str(db_path))

    issue_url = await SQLiteIssueTracker(settings).record(
        Finding(kind="broken-relative-link", path="docs/a.md", metadata={"target": "missing.md"})
    )

    assert issue_url.startswith(f"sqlite://{db_path}#curator_issues/")
    with sqlite3.connect(db_path) as db:
        row = db.execute("SELECT kind, path FROM curator_issues").fetchone()
    assert row == ("broken-relative-link", "docs/a.md")


def test_build_issue_tracker_selects_configured_tracker(tmp_path):
    settings = Settings(curator_issue_tracker="sqlite", curator_issue_db_path=str(tmp_path / "issues.db"))

    tracker = build_issue_tracker(settings)

    assert isinstance(tracker, SQLiteIssueTracker)
