import base64

import httpx

GITHUB_API = "https://api.github.com"


class GitHubContentSource:
    """Fetches markdown content from the configured GitHub repo for indexing.

    Mirrors mnemo-curator's tree-walk (mnemo_curator/github.py) rather than
    importing it: mnemo-core and mnemo-curator are separate deployables
    (ADR-012) with independent dependency trees, and the duplication is the
    accepted cost of that boundary (see ADR-013's precedent for versioned
    router packages).
    """

    def __init__(self, token: str, repo: str, docs_root: str = "", max_files: int = 2000) -> None:
        self._token = token
        self._repo = repo
        self._docs_root = docs_root.strip("/")
        self._max_files = max_files

    async def fetch(self, path: str, ref: str = "") -> str:
        params = {"ref": ref} if ref else None
        async with httpx.AsyncClient(
            base_url=GITHUB_API,
            headers=self._headers("application/vnd.github.raw+json"),
            timeout=30,
        ) as client:
            response = await client.get(f"/repos/{self._repo}/contents/{path}", params=params)
            response.raise_for_status()
            return response.text

    async def list_documents(self) -> list[tuple[str, str]]:
        headers = self._headers("application/vnd.github+json")
        async with httpx.AsyncClient(base_url=GITHUB_API, headers=headers, timeout=30) as client:
            repo_response = await client.get(f"/repos/{self._repo}")
            repo_response.raise_for_status()
            branch = repo_response.json()["default_branch"]

            tree_response = await client.get(
                f"/repos/{self._repo}/git/trees/{branch}",
                params={"recursive": "1"},
            )
            tree_response.raise_for_status()
            tree_data = tree_response.json()
            if tree_data.get("truncated"):
                raise RuntimeError(
                    f"GitHub tree for {self._repo}@{branch} was truncated; "
                    "repository is too large for a single recursive listing"
                )
            blobs = [
                (item["path"], item["sha"])
                for item in tree_data.get("tree", [])
                if item.get("type") == "blob"
                and item["path"].lower().endswith((".md", ".markdown"))
                and self._inside_docs_root(item["path"])
                and not self._is_template(item["path"])
            ][: self._max_files]

            documents: list[tuple[str, str]] = []
            for path, sha in blobs:
                response = await client.get(f"/repos/{self._repo}/git/blobs/{sha}")
                response.raise_for_status()
                data = response.json()
                if data.get("encoding") != "base64":
                    raise RuntimeError(
                        f"Unexpected encoding {data.get('encoding')!r} for blob {path} ({sha})"
                    )
                documents.append(
                    (path, base64.b64decode(data["content"]).decode("utf-8", errors="replace"))
                )
        return documents

    def _inside_docs_root(self, path: str) -> bool:
        return not self._docs_root or path.startswith(f"{self._docs_root}/")

    def _is_template(self, path: str) -> bool:
        # templates/ holds document-type definitions, not content (ADR-018)
        prefix = f"{self._docs_root}/templates/" if self._docs_root else "templates/"
        return path.startswith(prefix)

    def _headers(self, accept: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        }
