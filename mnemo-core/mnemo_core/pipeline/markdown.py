import re

from ..models import ProcessedDocument

DIATAXIS_FOLDERS: dict[str, str] = {
    "tutorial": "tutorials",
    "how-to": "how-to",
    "reference": "reference",
    "explanation": "explanation",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


def build_markdown(doc: ProcessedDocument) -> str:
    lines = ["---"]
    lines.append(f'title: "{doc.title}"')
    lines.append(f"type: {doc.type}")
    if doc.sub_label:
        lines.append(f"sub_label: {doc.sub_label}")
    lines.append(f"status: {doc.status}")
    lines.append(f"owner: {doc.owner}")
    lines.append(f'summary: "{doc.summary}"')
    lines.append(f"last_reviewed: {doc.last_reviewed}")
    lines.append("tags:")
    for tag in doc.tags:
        lines.append(f"  - {tag}")
    if doc.flags:
        lines.append("flags:")
        for flag in doc.flags:
            lines.append(f"  - {flag}")
    lines.append("---")
    lines.append("")
    lines.append(doc.body)
    return "\n".join(lines) + "\n"
