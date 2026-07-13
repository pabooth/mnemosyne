import base64

import httpx
import pytest

from mnemo_core.indexing.github import GitHubContentSource
from mnemo_core.pipeline.templates import (
    TemplateFetchError,
    fetch_template_set,
    parse_template,
)

VALID_TEMPLATE = """---
description: Rules the organisation mandates.
---

## Introduction

## Policies
"""


def test_parse_template_reads_type_sub_label_and_description():
    template = parse_template("templates/reference/standard.md", VALID_TEMPLATE)
    assert template.type == "reference"
    assert template.sub_label == "standard"
    assert template.description == "Rules the organisation mandates."
    assert template.body.startswith("## Introduction")


def test_parse_template_honours_docs_root_prefix():
    template = parse_template("kb/docs/templates/how-to/runbook.md", VALID_TEMPLATE)
    assert template.type == "how-to"
    assert template.sub_label == "runbook"


def test_parse_template_rejects_unknown_type_folder():
    with pytest.raises(TemplateFetchError, match="unknown type folder"):
        parse_template("templates/recipes/cake.md", VALID_TEMPLATE)


def test_parse_template_rejects_missing_description():
    content = "---\ntitle: nope\n---\n\n## Body\n"
    with pytest.raises(TemplateFetchError, match="description"):
        parse_template("templates/reference/standard.md", content)


def test_parse_template_rejects_missing_frontmatter():
    with pytest.raises(TemplateFetchError, match="frontmatter"):
        parse_template("templates/reference/standard.md", "## Just a body\n")


def _github_transport(tree_paths: dict[str, str], fail_tree: bool = False):
    """Mock the three GitHub calls the fetcher makes: repo, tree, blobs."""
    blobs = {
        f"sha-{i}": content for i, content in enumerate(tree_paths.values())
    }
    paths_to_sha = {
        path: f"sha-{i}" for i, path in enumerate(tree_paths.keys())
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/repos/acme/kb"):
            return httpx.Response(200, json={"default_branch": "main"})
        if "/git/trees/" in url:
            if fail_tree:
                return httpx.Response(500, json={"message": "boom"})
            return httpx.Response(
                200,
                json={
                    "truncated": False,
                    "tree": [
                        {"path": path, "sha": sha, "type": "blob"}
                        for path, sha in paths_to_sha.items()
                    ],
                },
            )
        if "/git/blobs/" in url:
            sha = url.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "encoding": "base64",
                    "content": base64.b64encode(blobs[sha].encode()).decode(),
                },
            )
        return httpx.Response(404, json={"message": f"unexpected: {url}"})

    return httpx.MockTransport(handler)


def test_fetch_template_set_loads_templates_under_templates_dir():
    transport = _github_transport(
        {
            "templates/reference/standard.md": VALID_TEMPLATE,
            "reference/some-content.md": "# Not a template",
            "notes.md": "# Not a template either",
        }
    )
    templates = fetch_template_set("tok", "acme/kb", transport=transport)
    assert len(templates) == 1
    assert templates.get("reference", "standard") is not None
    assert templates.sub_labels == ["standard"]


def test_fetch_template_set_respects_docs_root():
    transport = _github_transport(
        {
            "kb/docs/templates/how-to/runbook.md": VALID_TEMPLATE,
            "templates/reference/outside-root.md": VALID_TEMPLATE,
        }
    )
    templates = fetch_template_set("tok", "acme/kb", docs_root="kb/docs", transport=transport)
    assert len(templates) == 1
    assert templates.get("how-to", "runbook") is not None


def test_fetch_template_set_empty_when_no_templates_directory():
    transport = _github_transport({"reference/doc.md": "# Content"})
    templates = fetch_template_set("tok", "acme/kb", transport=transport)
    assert len(templates) == 0
    assert templates.sub_labels == []


def test_fetch_template_set_raises_on_http_failure():
    transport = _github_transport({}, fail_tree=True)
    with pytest.raises(TemplateFetchError, match="Failed to fetch templates"):
        fetch_template_set("tok", "acme/kb", transport=transport)


def test_fetch_template_set_raises_on_bad_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    with pytest.raises(TemplateFetchError, match="Failed to fetch templates"):
        fetch_template_set(
            "bad", "acme/kb", transport=httpx.MockTransport(handler)
        )


def test_fetch_template_set_raises_on_malformed_template():
    transport = _github_transport(
        {"templates/reference/broken.md": "## No frontmatter at all\n"}
    )
    with pytest.raises(TemplateFetchError, match="frontmatter"):
        fetch_template_set("tok", "acme/kb", transport=transport)


def test_indexer_content_source_excludes_templates():
    source = GitHubContentSource(token="t", repo="acme/kb")
    assert source._is_template("templates/reference/standard.md")
    assert not source._is_template("reference/a.md")

    rooted = GitHubContentSource(token="t", repo="acme/kb", docs_root="kb/docs")
    assert rooted._is_template("kb/docs/templates/how-to/runbook.md")
    assert not rooted._is_template("kb/docs/how-to/runbook.md")
    # a content folder that merely mentions templates is not excluded
    assert not rooted._is_template("templates/reference/standard.md")
