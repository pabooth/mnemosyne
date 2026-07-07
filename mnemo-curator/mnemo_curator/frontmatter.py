import re
from datetime import date

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(content: str) -> dict[str, str]:
    match = FRONTMATTER_RE.search(content)
    if not match:
        return {}
    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')
    return metadata


def title_from_content(path: str, content: str) -> str:
    metadata = parse_frontmatter(content)
    if metadata.get("title"):
        return metadata["title"]
    for line in content.splitlines():
        if line.startswith("# "):
            return line.removeprefix("# ").strip()
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("-", " ").strip() or "Untitled"


def owner_from_content(content: str, default: str = "unset") -> str:
    return parse_frontmatter(content).get("owner") or default


def set_frontmatter_value(content: str, key: str, value: str) -> str:
    match = FRONTMATTER_RE.search(content)
    if not match:
        return f"---\n{key}: {value}\n---\n\n{content.lstrip()}"

    lines = match.group(1).splitlines()
    replaced = False
    for index, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            lines[index] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{key}: {value}")
    frontmatter = "---\n" + "\n".join(lines) + "\n---\n"
    return frontmatter + content[match.end() :]


def set_reviewed_today(content: str) -> str:
    return set_frontmatter_value(content, "last_reviewed", date.today().isoformat())
