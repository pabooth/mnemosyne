import base64
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import httpx

from ..models import ProcessedDocument, PublishResult
from . import PublishError
from .markdown import DIATAXIS_FOLDERS, build_markdown, slugify

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class PublishPlan:
    repo: str
    file_path: str
    branch: str
    content_b64: str
    commit_message: str
    pr_title: str
    pr_body: str


class Publisher(Protocol):
    async def publish(self, doc: ProcessedDocument) -> PublishResult: ...


def build_publish_plan(
    doc: ProcessedDocument,
    repo: str,
    *,
    today: date | None = None,
    docs_root: str = "",
) -> PublishPlan:
    today = today or date.today()
    folder = DIATAXIS_FOLDERS.get(doc.type, "how-to")
    slug = slugify(doc.title)
    prefix = f"{docs_root.strip('/')}/" if docs_root else ""
    file_path = f"{prefix}{folder}/{slug}.md"
    branch = f"mnemo/{doc.type}/{slug}-{today.isoformat()}"
    content_b64 = base64.b64encode(build_markdown(doc).encode()).decode()

    return PublishPlan(
        repo=repo,
        file_path=file_path,
        branch=branch,
        content_b64=content_b64,
        commit_message=f"docs: add {doc.type} — {doc.title}",
        pr_title=f"[{doc.type}] {doc.title}",
        pr_body=(
            f"**Type:** {doc.type}\n"
            f"**Owner:** {doc.owner}\n"
            f"**Summary:** {doc.summary}\n\n"
            "Added by Mnemosyne ingestion pipeline."
        ),
    )


async def execute_publish_plan(
    plan: PublishPlan,
    token: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> PublishResult:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        if client is not None:
            pr_url = await _publish_with_client(client, plan)
        else:
            async with httpx.AsyncClient(
                base_url=GITHUB_API,
                headers=headers,
                timeout=30,
            ) as gh:
                pr_url = await _publish_with_client(gh, plan)

    except httpx.HTTPStatusError as e:
        raise PublishError(
            f"GitHub API error {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.RequestError as e:
        raise PublishError(f"GitHub API request failed: {e}") from e

    return PublishResult(
        pr_url=pr_url,
        branch=plan.branch,
        file_path=plan.file_path,
    )


async def _publish_with_client(client: httpx.AsyncClient, plan: PublishPlan) -> str:
    repo = plan.repo

    r = await client.get(f"/repos/{repo}")
    r.raise_for_status()
    default_branch = r.json()["default_branch"]

    r = await client.get(f"/repos/{repo}/git/ref/heads/{default_branch}")
    r.raise_for_status()
    sha = r.json()["object"]["sha"]

    r = await client.post(
        f"/repos/{repo}/git/refs",
        json={"ref": f"refs/heads/{plan.branch}", "sha": sha},
    )
    if r.status_code not in (201, 422):
        r.raise_for_status()

    r = await client.put(
        f"/repos/{repo}/contents/{plan.file_path}",
        json={
            "message": plan.commit_message,
            "content": plan.content_b64,
            "branch": plan.branch,
        },
    )
    r.raise_for_status()

    r = await client.post(
        f"/repos/{repo}/pulls",
        json={
            "title": plan.pr_title,
            "head": plan.branch,
            "base": default_branch,
            "body": plan.pr_body,
        },
    )
    if r.status_code == 422:
        owner = repo.split("/")[0]
        r2 = await client.get(
            f"/repos/{repo}/pulls",
            params={"head": f"{owner}:{plan.branch}", "state": "open"},
        )
        r2.raise_for_status()
        pulls = r2.json()
        if not pulls:
            raise PublishError(
                f"GitHub rejected PR creation (422) and no open PR found for branch {plan.branch!r}"
            )
        return pulls[0]["html_url"]

    r.raise_for_status()
    return r.json()["html_url"]


class GitHubPublisher:
    def __init__(
        self,
        github_token: str,
        github_repo: str,
        *,
        docs_root: str = "",
        today: date | None = None,
    ) -> None:
        self._token = github_token
        self._repo = github_repo
        self._docs_root = docs_root
        self._today = today

    async def publish(self, doc: ProcessedDocument) -> PublishResult:
        if not self._token:
            raise PublishError("GITHUB_TOKEN is not configured")
        if not self._repo:
            raise PublishError("GITHUB_REPO is not configured")

        plan = build_publish_plan(doc, self._repo, today=self._today, docs_root=self._docs_root)
        return await execute_publish_plan(plan, self._token)
