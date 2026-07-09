import hashlib
import re

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.DOTALL)
_HEADING = re.compile(r"(?m)^## ")


def strip_frontmatter(content: str) -> str:
    return _FRONTMATTER.sub("", content, count=1)


def chunk_markdown(content: str) -> list[str]:
    """Split a document into chunks along top-level (##) headings.

    Documents with no ## headings are indexed as a single chunk. Diataxis
    content (tutorials, how-tos, reference, explanations) consistently uses
    ## for its major sections, so this aligns chunk boundaries with the
    structure the pipeline already produces (see pipeline/markdown.py).
    """
    body = strip_frontmatter(content).strip()
    if not body:
        return []
    if not _HEADING.search(body):
        return [body]

    parts = _HEADING.split(body)
    chunks = []
    if parts[0].strip():
        chunks.append(parts[0].strip())
    chunks.extend(f"## {part.strip()}" for part in parts[1:] if part.strip())
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
