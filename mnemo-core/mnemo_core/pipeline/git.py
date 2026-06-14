"""Backward-compatible re-exports. Prefer markdown.py and publish.py."""

import warnings

from ..models import ProcessedDocument, PublishResult
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


async def commit_and_raise_pr(doc: ProcessedDocument) -> PublishResult:
    """Deprecated: use GitHubPublisher from publish.py."""
    warnings.warn(
        "commit_and_raise_pr is deprecated; use GitHubPublisher from publish.py instead",
        DeprecationWarning,
        stacklevel=2,
    )
    from ..config import get_settings

    publisher = GitHubPublisher(
        github_token=get_settings().github_token,
        github_repo=get_settings().github_repo,
    )
    return await publisher.publish(doc)
