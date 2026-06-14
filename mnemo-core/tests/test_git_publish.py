from datetime import date

import httpx
import pytest
import respx

from mnemo_core.pipeline import PublishError
from mnemo_core.pipeline.publish import GITHUB_API, build_publish_plan, execute_publish_plan
from tests.conftest import processed_doc


@respx.mock
async def test_execute_publish_plan_happy_path():
    doc = processed_doc()
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))

    respx.get(f"{GITHUB_API}/repos/acme/kb").mock(
        return_value=httpx.Response(200, json={"default_branch": "main"})
    )
    respx.get(f"{GITHUB_API}/repos/acme/kb/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "abc123"}})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/git/refs").mock(
        return_value=httpx.Response(201, json={})
    )
    respx.put(f"{GITHUB_API}/repos/acme/kb/contents/{plan.file_path}").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/pulls").mock(
        return_value=httpx.Response(
            201,
            json={"html_url": "https://github.com/acme/kb/pull/42"},
        )
    )

    result = await execute_publish_plan(plan, "gh-test")

    assert result.pr_url == "https://github.com/acme/kb/pull/42"
    assert result.branch == plan.branch
    assert result.file_path == plan.file_path


@respx.mock
async def test_execute_publish_plan_reuses_existing_pr_on_422():
    doc = processed_doc()
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))

    respx.get(f"{GITHUB_API}/repos/acme/kb").mock(
        return_value=httpx.Response(200, json={"default_branch": "main"})
    )
    respx.get(f"{GITHUB_API}/repos/acme/kb/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "abc123"}})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/git/refs").mock(
        return_value=httpx.Response(422, json={})
    )
    respx.put(f"{GITHUB_API}/repos/acme/kb/contents/{plan.file_path}").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/pulls").mock(
        return_value=httpx.Response(422, json={})
    )
    respx.get(f"{GITHUB_API}/repos/acme/kb/pulls").mock(
        return_value=httpx.Response(
            200,
            json=[{"html_url": "https://github.com/acme/kb/pull/99"}],
        )
    )

    result = await execute_publish_plan(plan, "gh-test")
    assert result.pr_url == "https://github.com/acme/kb/pull/99"


@respx.mock
async def test_execute_publish_plan_raises_on_422_with_empty_pr_list():
    doc = processed_doc()
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))

    respx.get(f"{GITHUB_API}/repos/acme/kb").mock(
        return_value=httpx.Response(200, json={"default_branch": "main"})
    )
    respx.get(f"{GITHUB_API}/repos/acme/kb/git/ref/heads/main").mock(
        return_value=httpx.Response(200, json={"object": {"sha": "abc123"}})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/git/refs").mock(
        return_value=httpx.Response(201, json={})
    )
    respx.put(f"{GITHUB_API}/repos/acme/kb/contents/{plan.file_path}").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.post(f"{GITHUB_API}/repos/acme/kb/pulls").mock(
        return_value=httpx.Response(422, json={})
    )
    respx.get(f"{GITHUB_API}/repos/acme/kb/pulls").mock(
        return_value=httpx.Response(200, json=[])
    )

    with pytest.raises(PublishError, match="no open PR found"):
        await execute_publish_plan(plan, "gh-test")


async def test_github_publisher_requires_token():
    from mnemo_core.pipeline.publish import GitHubPublisher

    publisher = GitHubPublisher(github_token="", github_repo="acme/kb")
    with pytest.raises(PublishError, match="GITHUB_TOKEN"):
        await publisher.publish(processed_doc())


async def test_github_publisher_requires_repo():
    from mnemo_core.pipeline.publish import GitHubPublisher

    publisher = GitHubPublisher(github_token="gh-test", github_repo="")
    with pytest.raises(PublishError, match="GITHUB_REPO"):
        await publisher.publish(processed_doc())
