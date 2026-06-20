import base64
import posixpath
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import PurePosixPath

import httpx

from .config import Settings
from .pipeline import PublishError

LINK_RE = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:|#)([^)#]+)")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


async def audit_knowledge_base(cfg: Settings) -> dict:
    if not cfg.github_token or not cfg.github_repo:
        raise PublishError("GITHUB_TOKEN and GITHUB_REPO are required for self-audit")
    headers = {
        "Authorization": f"Bearer {cfg.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(
        base_url="https://api.github.com", headers=headers, timeout=30
    ) as client:
        repo_response = await client.get(f"/repos/{cfg.github_repo}")
        repo_response.raise_for_status()
        branch = repo_response.json()["default_branch"]
        tree_response = await client.get(
            f"/repos/{cfg.github_repo}/git/trees/{branch}", params={"recursive": "1"}
        )
        tree_response.raise_for_status()
        paths = [
            item["path"]
            for item in tree_response.json().get("tree", [])
            if item.get("type") == "blob"
            and item["path"].lower().endswith((".md", ".markdown"))
            and (not cfg.docs_root or item["path"].startswith(cfg.docs_root.strip("/") + "/"))
        ][: cfg.audit_max_files]

        documents: dict[str, str] = {}
        for path in paths:
            response = await client.get(
                f"/repos/{cfg.github_repo}/contents/{path}", params={"ref": branch}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("encoding") == "base64":
                documents[path] = base64.b64decode(data["content"]).decode(
                    "utf-8", errors="replace"
                )

    findings: list[dict] = []
    titles: Counter[str] = Counter()
    known_paths = set(documents)
    stale_before = date.today() - timedelta(days=cfg.audit_stale_after_days)

    for path, content in documents.items():
        metadata = _frontmatter(content)
        title = metadata.get("title", "").strip('"').lower()
        if title:
            titles[title] += 1
        if not metadata.get("owner"):
            findings.append({"path": path, "kind": "missing-owner"})
        reviewed = metadata.get("last_reviewed", "")
        try:
            if date.fromisoformat(reviewed) < stale_before:
                findings.append({"path": path, "kind": "stale", "last_reviewed": reviewed})
        except ValueError:
            findings.append({"path": path, "kind": "invalid-review-date", "value": reviewed})
        for target in LINK_RE.findall(content):
            resolved = posixpath.normpath(str(PurePosixPath(path).parent.joinpath(target)))
            if resolved not in known_paths:
                findings.append(
                    {"path": path, "kind": "broken-relative-link", "target": target}
                )

    for title, count in titles.items():
        if count > 1:
            findings.append({"kind": "duplicate-title", "title": title, "count": count})

    return {
        "repository": cfg.github_repo,
        "documents_scanned": len(documents),
        "findings": findings,
    }


def _frontmatter(content: str) -> dict[str, str]:
    match = FRONTMATTER_RE.search(content)
    if not match:
        return {}
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata
