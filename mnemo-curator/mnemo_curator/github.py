import base64

import httpx

from .models import Document
from .settings import Settings


class GitHubClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def list_documents(self) -> list[Document]:
        if not self.settings.github_token or not self.settings.github_repo:
            raise RuntimeError("GITHUB_TOKEN and GITHUB_REPO are required")
        headers = self._headers("application/vnd.github+json")
        async with httpx.AsyncClient(base_url="https://api.github.com", headers=headers, timeout=30) as client:
            repo_response = await client.get(f"/repos/{self.settings.github_repo}")
            repo_response.raise_for_status()
            branch = repo_response.json()["default_branch"]
            tree_response = await client.get(
                f"/repos/{self.settings.github_repo}/git/trees/{branch}",
                params={"recursive": "1"},
            )
            tree_response.raise_for_status()
            tree_data = tree_response.json()
            if tree_data.get("truncated"):
                raise RuntimeError(
                    f"GitHub tree for {self.settings.github_repo}@{branch} was truncated; "
                    "repository is too large for a single recursive listing"
                )
            blobs = [
                (item["path"], item["sha"])
                for item in tree_data.get("tree", [])
                if item.get("type") == "blob"
                and item["path"].lower().endswith((".md", ".markdown"))
                and self._inside_docs_root(item["path"])
            ][: self.settings.curator_max_files]

            documents: list[Document] = []
            for path, sha in blobs:
                # The Git Blob API (unlike Contents) always returns base64 for
                # text/binary blobs up to 100MB, so large docs aren't silently skipped.
                response = await client.get(f"/repos/{self.settings.github_repo}/git/blobs/{sha}")
                response.raise_for_status()
                data = response.json()
                if data.get("encoding") != "base64":
                    raise RuntimeError(
                        f"Unexpected encoding {data.get('encoding')!r} for blob {path} ({sha})"
                    )
                documents.append(
                    Document(
                        path=path,
                        content=base64.b64decode(data["content"]).decode("utf-8", errors="replace"),
                    )
                )
        return documents

    def _inside_docs_root(self, path: str) -> bool:
        root = self.settings.docs_root.strip("/")
        return not root or path.startswith(f"{root}/")

    def _headers(self, accept: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
