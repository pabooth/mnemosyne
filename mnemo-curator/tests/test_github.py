import base64

import pytest
import respx
from httpx import Response

from mnemo_curator.github import GitHubClient
from mnemo_curator.settings import Settings


def _mock_repo_and_tree(tree_items, truncated=False):
    respx.get("https://api.github.com/repos/owner/repo").mock(
        return_value=Response(200, json={"default_branch": "main"})
    )
    respx.get("https://api.github.com/repos/owner/repo/git/trees/main").mock(
        return_value=Response(200, json={"tree": tree_items, "truncated": truncated})
    )


def _mock_contents(path, *, encoding="base64", content=""):
    body = {"encoding": encoding}
    if encoding == "base64":
        body["content"] = base64.b64encode(content.encode("utf-8")).decode("ascii")
    respx.get(f"https://api.github.com/repos/owner/repo/contents/{path}").mock(
        return_value=Response(200, json=body)
    )


async def test_list_documents_returns_matching_markdown_documents():
    settings = Settings(github_token="token", github_repo="owner/repo")
    tree_items = [
        {"path": "docs/a.md", "type": "blob"},
        {"path": "docs/b.markdown", "type": "blob"},
        {"path": "docs/image.png", "type": "blob"},
        {"path": "docs/subdir", "type": "tree"},
    ]

    with respx.mock:
        _mock_repo_and_tree(tree_items)
        _mock_contents("docs/a.md", content="A body")
        _mock_contents("docs/b.markdown", content="B body")

        documents = await GitHubClient(settings).list_documents()

    assert {doc.path for doc in documents} == {"docs/a.md", "docs/b.markdown"}
    assert {doc.content for doc in documents} == {"A body", "B body"}


async def test_list_documents_excludes_paths_outside_docs_root():
    settings = Settings(github_token="token", github_repo="owner/repo", docs_root="docs")
    tree_items = [
        {"path": "docs/a.md", "type": "blob"},
        {"path": "other/b.md", "type": "blob"},
    ]

    with respx.mock:
        _mock_repo_and_tree(tree_items)
        _mock_contents("docs/a.md", content="A body")

        documents = await GitHubClient(settings).list_documents()

    assert [doc.path for doc in documents] == ["docs/a.md"]


async def test_list_documents_respects_curator_max_files():
    settings = Settings(github_token="token", github_repo="owner/repo", curator_max_files=1)
    tree_items = [
        {"path": "docs/a.md", "type": "blob"},
        {"path": "docs/b.md", "type": "blob"},
    ]

    with respx.mock:
        _mock_repo_and_tree(tree_items)
        _mock_contents("docs/a.md", content="A body")

        documents = await GitHubClient(settings).list_documents()

    assert [doc.path for doc in documents] == ["docs/a.md"]


async def test_list_documents_skips_contents_without_base64_encoding():
    settings = Settings(github_token="token", github_repo="owner/repo")
    tree_items = [
        {"path": "docs/a.md", "type": "blob"},
        {"path": "docs/huge.md", "type": "blob"},
    ]

    with respx.mock:
        _mock_repo_and_tree(tree_items)
        _mock_contents("docs/a.md", content="A body")
        _mock_contents("docs/huge.md", encoding="none")

        documents = await GitHubClient(settings).list_documents()

    assert [doc.path for doc in documents] == ["docs/a.md"]


async def test_list_documents_ignores_truncated_tree_flag():
    settings = Settings(github_token="token", github_repo="owner/repo")
    tree_items = [{"path": "docs/a.md", "type": "blob"}]

    with respx.mock:
        _mock_repo_and_tree(tree_items, truncated=True)
        _mock_contents("docs/a.md", content="A body")

        documents = await GitHubClient(settings).list_documents()

    assert [doc.path for doc in documents] == ["docs/a.md"]


async def test_list_documents_requires_token_and_repo():
    settings = Settings(github_token="", github_repo="")

    with pytest.raises(RuntimeError):
        await GitHubClient(settings).list_documents()


def test_inside_docs_root_matches_configured_root():
    settings = Settings(docs_root="docs")
    client = GitHubClient(settings)

    assert client._inside_docs_root("docs/a.md") is True
    assert client._inside_docs_root("other/a.md") is False


def test_inside_docs_root_allows_all_paths_when_unset():
    client = GitHubClient(Settings(docs_root=""))

    assert client._inside_docs_root("anything/a.md") is True


def test_headers_include_auth_and_accept():
    client = GitHubClient(Settings(github_token="token"))

    headers = client._headers("application/vnd.github+json")

    assert headers["Authorization"] == "Bearer token"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"
