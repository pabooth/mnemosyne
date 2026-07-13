"""KB-owned document templates and sub-label taxonomy (ADR-018).

Templates live in the knowledge-base repository under
``<DOCS_ROOT>/templates/<type-folder>/<sub-label>.md``. The fetched set
defines the sub-label taxonomy: the classifier prompt is assembled from
it, and an absent or empty ``templates/`` directory is a valid empty
taxonomy. Any fetch failure is fatal at startup — mnemo-core exits
rather than running against a knowledge base it cannot read.
"""

import base64
import logging
import re
from dataclasses import dataclass

import httpx

from .markdown import DIATAXIS_FOLDERS

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
TEMPLATES_DIR = "templates"

# Guardrails: descriptions are injected into every classification prompt
# and the whole set is held in memory, so a runaway KB must fail loudly
# rather than silently inflate prompts (project input-limits guideline).
MAX_TEMPLATE_COUNT = 100
MAX_TEMPLATE_BYTES = 65_536
MAX_DESCRIPTION_CHARS = 500

_FOLDER_TO_TYPE = {folder: doc_type for doc_type, folder in DIATAXIS_FOLDERS.items()}

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DESCRIPTION = re.compile(r"^description:\s*(.+)$", re.MULTILINE)


class TemplateFetchError(Exception):
    """Raised when the template set cannot be fetched or parsed."""


@dataclass(frozen=True)
class Template:
    type: str
    sub_label: str
    description: str
    body: str


class TemplateSet:
    def __init__(self, templates: list[Template]) -> None:
        self._templates = list(templates)
        self._by_key: dict[tuple[str, str], Template] = {}
        for template in self._templates:
            key = (template.type, template.sub_label)
            if key in self._by_key:
                raise TemplateFetchError(
                    f"Duplicate template for {template.type}/{template.sub_label}; "
                    "each (type, sub-label) pair must be defined exactly once"
                )
            self._by_key[key] = template

    def __len__(self) -> int:
        return len(self._templates)

    def get(self, doc_type: str, sub_label: str) -> Template | None:
        return self._by_key.get((doc_type, sub_label))

    def for_type(self, doc_type: str) -> list[Template]:
        return [t for t in self._templates if t.type == doc_type]

    @property
    def sub_labels(self) -> list[str]:
        return sorted({t.sub_label for t in self._templates})


def parse_template(path: str, content: str) -> Template:
    """Parse one ``templates/<type-folder>/<sub-label>.md`` file.

    The directory names the Diataxis type, the filename names the
    sub-label, and the frontmatter ``description`` is the classifier's
    knowledge of when the type applies — a missing description is an
    error, not a default, because it silently degrades classification.
    """
    segments = path.strip("/").split("/")
    # .../templates/<type-folder>/<sub-label>.md
    try:
        templates_index = segments.index(TEMPLATES_DIR)
        folder, filename = segments[templates_index + 1 :]
    except ValueError as e:
        raise TemplateFetchError(
            f"Template path {path!r} is not of the form "
            f"{TEMPLATES_DIR}/<type>/<sub-label>.md"
        ) from e

    doc_type = _FOLDER_TO_TYPE.get(folder)
    if doc_type is None:
        raise TemplateFetchError(
            f"Template {path!r} sits under unknown type folder {folder!r}; "
            f"expected one of: {', '.join(sorted(DIATAXIS_FOLDERS.values()))}"
        )

    sub_label = filename.removesuffix(".md").removesuffix(".markdown")

    frontmatter = _FRONTMATTER.match(content)
    if frontmatter is None:
        raise TemplateFetchError(f"Template {path!r} has no frontmatter block")
    description_match = _DESCRIPTION.search(frontmatter.group(1))
    if description_match is None:
        raise TemplateFetchError(
            f"Template {path!r} has no 'description' in its frontmatter; the "
            "description tells the classifier when this document type applies"
        )
    description = description_match.group(1).strip().strip("\"'")
    if not description or description in ("|", ">", "|-", ">-", "|+", ">+"):
        raise TemplateFetchError(
            f"Template {path!r} has an empty or block-scalar 'description'; "
            "write it as a single-line frontmatter value"
        )
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise TemplateFetchError(
            f"Template {path!r} description exceeds {MAX_DESCRIPTION_CHARS} "
            "characters; it is injected into every classification prompt, "
            "so keep it a concise definition"
        )
    body = content[frontmatter.end() :].strip("\n")

    return Template(type=doc_type, sub_label=sub_label, description=description, body=body)


def fetch_template_set(
    token: str,
    repo: str,
    docs_root: str = "",
    transport: httpx.BaseTransport | None = None,
) -> TemplateSet:
    """Fetch every template from the KB repository's templates directory.

    Raises TemplateFetchError on any failure — credentials, repository,
    network, or a malformed template file. An existing-but-empty (or
    absent) templates directory returns an empty set.
    """
    root = docs_root.strip("/")
    prefix = f"{root}/{TEMPLATES_DIR}/" if root else f"{TEMPLATES_DIR}/"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        with httpx.Client(
            base_url=GITHUB_API, headers=headers, timeout=30, transport=transport
        ) as client:
            repo_response = client.get(f"/repos/{repo}")
            repo_response.raise_for_status()
            branch = repo_response.json()["default_branch"]

            tree_response = client.get(
                f"/repos/{repo}/git/trees/{branch}", params={"recursive": "1"}
            )
            tree_response.raise_for_status()
            tree_data = tree_response.json()
            if tree_data.get("truncated"):
                raise TemplateFetchError(
                    f"GitHub tree for {repo}@{branch} was truncated; "
                    "repository is too large for a single recursive listing"
                )

            paths = [
                (item["path"], item["sha"])
                for item in tree_data.get("tree", [])
                if item.get("type") == "blob"
                and item["path"].startswith(prefix)
                and item["path"].lower().endswith((".md", ".markdown"))
            ]
            if len(paths) > MAX_TEMPLATE_COUNT:
                raise TemplateFetchError(
                    f"Knowledge base defines {len(paths)} templates; the limit "
                    f"is {MAX_TEMPLATE_COUNT} because every description is "
                    "injected into the classification prompt"
                )

            templates = []
            for path, sha in paths:
                blob_response = client.get(f"/repos/{repo}/git/blobs/{sha}")
                blob_response.raise_for_status()
                data = blob_response.json()
                if data.get("encoding") != "base64":
                    raise TemplateFetchError(
                        f"Unexpected encoding {data.get('encoding')!r} for template {path}"
                    )
                raw = base64.b64decode(data["content"])
                if len(raw) > MAX_TEMPLATE_BYTES:
                    raise TemplateFetchError(
                        f"Template {path} is {len(raw)} bytes; the limit is "
                        f"{MAX_TEMPLATE_BYTES} bytes"
                    )
                content = raw.decode("utf-8", errors="replace")
                templates.append(parse_template(path, content))
    except httpx.HTTPError as e:
        raise TemplateFetchError(f"Failed to fetch templates from {repo}: {e}") from e

    return TemplateSet(templates)


_template_set_override: TemplateSet | None = None
_template_set_cache: TemplateSet | None = None


def get_template_set() -> TemplateSet:
    """Return the template set, fetching it on first use (ADR-018).

    Without a configured GitHub repository and token there is nothing to
    fetch: preview-only deployments get an empty taxonomy and a warning.
    A configured deployment that cannot fetch raises TemplateFetchError,
    which is fatal at startup by design.
    """
    global _template_set_cache
    if _template_set_override is not None:
        return _template_set_override
    if _template_set_cache is None:
        from ..config import get_settings

        cfg = get_settings()
        if not cfg.github_token or not cfg.github_repo:
            logger.warning(
                "GITHUB_TOKEN/GITHUB_REPO not configured; starting with an "
                "empty template set and no sub-label taxonomy"
            )
            _template_set_cache = TemplateSet([])
        else:
            _template_set_cache = fetch_template_set(
                cfg.github_token, cfg.github_repo, cfg.docs_root
            )
            if len(_template_set_cache) == 0:
                logger.info(
                    "Knowledge base %s has no templates/ directory; using an "
                    "empty sub-label taxonomy",
                    cfg.github_repo,
                )
            else:
                logger.info(
                    "Loaded %d templates from %s: %s",
                    len(_template_set_cache),
                    cfg.github_repo,
                    ", ".join(_template_set_cache.sub_labels),
                )
    return _template_set_cache


def configure_template_set(override: TemplateSet | None) -> None:
    global _template_set_override, _template_set_cache
    _template_set_override = override
    _template_set_cache = None
