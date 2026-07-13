from fastapi import Depends

from ..config import Settings, get_settings
from ..embeddings.factory import get_embedding_provider
from ..indexing.github import GitHubContentSource
from ..indexing.service import Indexer
from ..llm.base import LLMProvider
from ..llm.factory import get_provider
from ..pipeline.dedup import DuplicateChecker
from ..pipeline.publish import GitHubPublisher, Publisher
from ..pipeline.runner import PipelineRunner
from ..pipeline.templates import TemplateSet, get_template_set
from ..vector.factory import get_vector_index


def build_runner(
    cfg: Settings | None = None,
    publisher: Publisher | None = None,
    llm: LLMProvider | None = None,
    dedup: DuplicateChecker | None = None,
) -> PipelineRunner:
    cfg = get_settings() if cfg is None else cfg
    if publisher is None:
        publisher = GitHubPublisher(
            github_token=cfg.github_token,
            github_repo=cfg.github_repo,
            docs_root=cfg.docs_root,
        )
    if llm is None:
        llm = get_provider(cfg)
    if dedup is None and cfg.dedup_enabled:
        dedup = build_dedup_checker(cfg)
    return PipelineRunner(
        llm,
        publisher,
        dedup=dedup,
        timeout_seconds=cfg.request_timeout_seconds,
        templates=get_template_set(),
    )


def get_publisher(cfg: Settings = Depends(get_settings)) -> Publisher:
    return GitHubPublisher(
        github_token=cfg.github_token,
        github_repo=cfg.github_repo,
        docs_root=cfg.docs_root,
    )


def get_llm(cfg: Settings = Depends(get_settings)) -> LLMProvider:
    return get_provider(cfg)


def build_dedup_checker(cfg: Settings | None = None) -> DuplicateChecker:
    cfg = get_settings() if cfg is None else cfg
    return DuplicateChecker(
        vector_index=get_vector_index(cfg),
        embedding=get_embedding_provider(cfg),
        max_distance=cfg.dedup_max_distance,
        top_k=cfg.dedup_top_k,
    )


def get_dedup_checker(cfg: Settings = Depends(get_settings)) -> DuplicateChecker | None:
    if not cfg.dedup_enabled:
        return None
    return build_dedup_checker(cfg)


def get_runner(
    publisher: Publisher = Depends(get_publisher),
    llm: LLMProvider = Depends(get_llm),
    dedup: DuplicateChecker | None = Depends(get_dedup_checker),
    cfg: Settings = Depends(get_settings),
    templates: TemplateSet = Depends(get_template_set),
) -> PipelineRunner:
    return PipelineRunner(
        llm,
        publisher,
        dedup=dedup,
        timeout_seconds=cfg.request_timeout_seconds,
        templates=templates,
    )


def build_indexer(cfg: Settings | None = None) -> Indexer:
    cfg = get_settings() if cfg is None else cfg
    return Indexer(
        vector_index=get_vector_index(cfg),
        embedding=get_embedding_provider(cfg),
        content_source=GitHubContentSource(
            token=cfg.github_token,
            repo=cfg.github_repo,
            docs_root=cfg.docs_root,
            max_files=cfg.index_max_files,
        ),
    )


def get_indexer(cfg: Settings = Depends(get_settings)) -> Indexer:
    return build_indexer(cfg)
