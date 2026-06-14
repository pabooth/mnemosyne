"""Backward-compatible re-exports. Prefer markdown.py and publish.py."""

from .markdown import DIATAXIS_FOLDERS, build_markdown, slugify
from .publish import GitHubPublisher, build_publish_plan, execute_publish_plan

__all__ = [
    "DIATAXIS_FOLDERS",
    "GitHubPublisher",
    "build_markdown",
    "build_publish_plan",
    "execute_publish_plan",
    "slugify",
]


async def commit_and_raise_pr(doc):  # type: ignore[no-untyped-def]
    """Deprecated: use GitHubPublisher from publish.py."""
    from ..config import get_settings

    publisher = GitHubPublisher(
        github_token=get_settings().github_token,
        github_repo=get_settings().github_repo,
    )
    return await publisher.publish(doc)
