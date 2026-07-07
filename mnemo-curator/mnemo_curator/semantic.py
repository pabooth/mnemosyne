import json

import httpx

from .models import Finding
from .settings import Settings


class SemanticResolver:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def rewrite(self, content: str, finding: Finding) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for semantic resolution")

        prompt = (
            "Rewrite this Markdown document to resolve the finding below. "
            "Preserve factual claims, frontmatter, headings, links, and code blocks. "
            "Return only the complete corrected Markdown document.\n\n"
            f"Finding: {finding.detail}\n"
            f"Metadata: {json.dumps(finding.metadata, sort_keys=True)}\n\n"
            f"Document:\n{content}"
        )
        async with httpx.AsyncClient(
            base_url=self.settings.openai_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            timeout=120,
        ) as client:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.settings.openai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a careful documentation curator. Return corrected Markdown only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
