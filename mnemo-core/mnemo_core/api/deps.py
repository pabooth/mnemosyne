from fastapi import Depends

from ..config import Settings, get_settings
from ..embeddings.factory import get_embedding_provider
from ..indexing.github import GitHubContentSource
from ..indexing.service import Indexer
from ..llm.base import LLMProvider
from ..llm.factory import get_provider, get_provider_for
from ..pipeline.dedup import DuplicateChecker
from ..pipeline.publish import GitHubPublisher, Publisher
from ..pipeline.review import AdversarialReviewer, GitHubReviewAuditSink
from ..pipeline.runner import PipelineRunner
from ..pipeline.templates import TemplateSet, get_template_set
from ..vector.factory import get_vector_index


class _DeferredProvider(LLMProvider):
    """Delay credential validation until the reviewer is actually invoked."""

    def __init__(self, family: str, model: str, cfg: Settings) -> None:
        self._family = family
        self._model = model
        self._cfg = cfg

    async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        provider = get_provider_for(self._family, self._model, self._cfg)
        return await provider.complete(system, user, max_tokens)


def build_runner(
    cfg: Settings | None = None,
    publisher: Publisher | None = None,
    llm: LLMProvider | None = None,
    dedup: DuplicateChecker | None = None,
    reviewer: AdversarialReviewer | None = None,
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
    if reviewer is None and cfg.adversarial_review_enabled:
        reviewer = build_adversarial_reviewer(cfg)
    return PipelineRunner(
        llm,
        publisher,
        dedup=dedup,
        timeout_seconds=cfg.request_timeout_seconds,
        templates=get_template_set(),
        reviewer=reviewer,
    )


def build_adversarial_reviewer(cfg: Settings | None = None) -> AdversarialReviewer:
    cfg = get_settings() if cfg is None else cfg
    return AdversarialReviewer(
        _DeferredProvider(
            cfg.reviewer_advocate_provider,
            cfg.reviewer_advocate_model,
            cfg,
        ),
        _DeferredProvider(
            cfg.reviewer_critic_provider,
            cfg.reviewer_critic_model,
            cfg,
        ),
        advocate_family=cfg.reviewer_advocate_provider,
        critic_family=cfg.reviewer_critic_provider,
        audit_sink=GitHubReviewAuditSink(cfg.github_token, cfg.github_repo),
    )


def get_publisher(cfg: Settings = Depends(get_settings)) -> Publisher:
    return GitHubPublisher(
        github_token=cfg.github_token,
        github_repo=cfg.github_repo,
        docs_root=cfg.docs_root,
    )


def get_llm(cfg: Settings = Depends(get_settings)) -> LLMProvider:
    return get_provider(cfg)


def get_reviewer(
    cfg: Settings = Depends(get_settings),
) -> AdversarialReviewer | None:
    if not cfg.adversarial_review_enabled:
        return None
    return build_adversarial_reviewer(cfg)


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
    reviewer: AdversarialReviewer | None = Depends(get_reviewer),
) -> PipelineRunner:
    return PipelineRunner(
        llm,
        publisher,
        dedup=dedup,
        timeout_seconds=cfg.request_timeout_seconds,
        templates=templates,
        reviewer=reviewer,
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
