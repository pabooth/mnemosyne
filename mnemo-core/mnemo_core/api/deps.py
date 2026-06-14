from fastapi import Depends

from ..config import Settings, get_settings
from ..llm.base import LLMProvider
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


def get_llm(cfg: Settings = Depends(get_settings)) -> LLMProvider:
    return get_provider(cfg)


def get_runner(
    publisher: Publisher = Depends(get_publisher),
    llm: LLMProvider = Depends(get_llm),
) -> PipelineRunner:
    return PipelineRunner(llm, publisher)
