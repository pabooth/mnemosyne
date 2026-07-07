import json

import httpx

from .frontmatter import FRONTMATTER_RE
from .models import Finding
from .settings import Settings

MAX_REWRITE_SIZE_MULTIPLIER = 3
MIN_REWRITE_MAX_SIZE = 50_000


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
        rewritten = str(data["choices"][0]["message"]["content"]).strip()
        return self._validate(content, rewritten)

    def _validate(self, original: str, rewritten: str) -> str:
        if not rewritten:
            raise RuntimeError("Semantic rewrite returned empty content")

        max_size = max(len(original) * MAX_REWRITE_SIZE_MULTIPLIER, MIN_REWRITE_MAX_SIZE)
        if len(rewritten) > max_size:
            raise RuntimeError(f"Semantic rewrite exceeded maximum size of {max_size} characters")

        if FRONTMATTER_RE.search(original) and not FRONTMATTER_RE.search(rewritten):
            raise RuntimeError("Semantic rewrite dropped the document's frontmatter")

        return rewritten
