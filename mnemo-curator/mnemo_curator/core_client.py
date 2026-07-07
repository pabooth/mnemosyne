import httpx

from .frontmatter import owner_from_content, title_from_content
from .models import Document
from .settings import Settings


class MnemoCoreClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def submit(self, document: Document) -> str:
        if not self.settings.mnemo_api_token:
            raise RuntimeError("MNEMO_API_TOKEN is required to submit curator fixes")
        payload = {
            "title": title_from_content(document.path, document.content),
            "owner": owner_from_content(document.content, self.settings.curator_default_owner),
            "content": document.content,
        }
        async with httpx.AsyncClient(
            base_url=self.settings.mnemo_core_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.settings.mnemo_api_token}"},
            timeout=120,
        ) as client:
            response = await client.post("/api/v1/ingest", json=payload)
            response.raise_for_status()
        data = response.json()
        return str(data.get("id") or data.get("publish", {}).get("pr_url") or "")
