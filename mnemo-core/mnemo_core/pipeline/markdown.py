import json
import re

from ..models import ProcessedDocument

DIATAXIS_FOLDERS: dict[str, str] = {
    "tutorial": "tutorials",
    "how-to": "how-to",
    "reference": "reference",
    "explanation": "explanation",
}

# Characters that require a YAML scalar to be quoted.
_YAML_UNSAFE = re.compile(r'[:#\[\]{}&*!|>\'"%@`]|^[-?:,]|\s')


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


def quote_yaml_str(value: str) -> str:
    """Return a safely double-quoted YAML scalar using JSON encoding.

    JSON strings are valid YAML double-quoted scalars for all characters
    in the Unicode Basic Multilingual Plane, which covers all values produced
    by this pipeline.
    """
    return json.dumps(value)


def _yaml_scalar(value: str) -> str:
    """Quote only when the value contains YAML-unsafe characters."""
    if not value or _YAML_UNSAFE.search(value):
        return quote_yaml_str(value)
    return value


def build_markdown(doc: ProcessedDocument) -> str:
    lines = ["---"]
    lines.append(f"title: {quote_yaml_str(doc.title)}")
    lines.append(f"type: {doc.type}")
    if doc.sub_label:
        lines.append(f"sub_label: {doc.sub_label}")
    lines.append(f"status: {doc.status}")
    lines.append(f"owner: {doc.owner}")
    lines.append(f"summary: {quote_yaml_str(doc.summary)}")
    lines.append(f"last_reviewed: {doc.last_reviewed}")
    lines.append("tags:")
    for tag in doc.tags:
        lines.append(f"  - {_yaml_scalar(tag)}")
    if doc.flags:
        lines.append("flags:")
        for flag in doc.flags:
            lines.append(f"  - {_yaml_scalar(flag)}")
    lines.append("---")
    lines.append("")
    lines.append(doc.body)
    return "\n".join(lines) + "\n"
