from fastapi import Depends

from ..llm.base import LLMProvider
from ..config import Settings, get_settings
from ..llm.factory import get_provider
from ..pipeline.publish import GitHubPublisher, Publisher
from ..pipeline.runner import PipelineRunner


def build_runner(
    cfg: Settings | None = None,
    publisher: Publisher | None = None,
    llm: LLMProvider | None = None,
) -> PipelineRunner:
    cfg = get_settings() if cfg is None else cfg
    if publisher is None:
        publisher = GitHubPublisher(
            github_token=cfg.github_token,
            github_repo=cfg.github_repo,
        )
    if llm is None:
        llm = get_provider(cfg)
    return PipelineRunner(llm, publisher)


def get_publisher(cfg: Settings = Depends(get_settings)) -> Publisher:
    return GitHubPublisher(
        github_token=cfg.github_token,
        github_repo=cfg.github_repo,
    )


def get_runner(
    cfg: Settings = Depends(get_settings),
    publisher: Publisher = Depends(get_publisher),
) -> PipelineRunner:
    return build_runner(cfg, publisher)
