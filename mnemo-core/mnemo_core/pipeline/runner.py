import asyncio
import logging
import time
from typing import Any, Protocol

from opentelemetry import metrics

from ..llm.base import LLMProvider
from ..models import (
    AdversarialReviewResult,
    DocumentInput,
    IngestResult,
    ProcessedDocument,
    PublishResult,
)
from . import ProcessingError, PublishError
from .classify import classify_augment_format
from .dedup import DuplicateChecker
from .publish import Publisher
from .review import AdversarialReviewer
from .templates import TemplateSet

logger = logging.getLogger(__name__)


class ReviewJobStore(Protocol):
    def create_review_job(
        self, document: ProcessedDocument, published: PublishResult
    ) -> dict[str, Any]: ...

    def list_pending_review_jobs(self) -> list[dict[str, Any]]: ...

    def get_review_job(self, pr_url: str) -> dict[str, Any] | None: ...

    def claim_review_job(self, pr_url: str) -> bool: ...

    def finish_review_job(
        self,
        pr_url: str,
        *,
        result: AdversarialReviewResult | None = None,
        error: str | None = None,
    ) -> None: ...


class PipelineRunner:
    def __init__(
        self,
        llm: LLMProvider,
        publisher: Publisher,
        dedup: DuplicateChecker | None = None,
        timeout_seconds: float = 120,
        templates: TemplateSet | None = None,
        reviewer: AdversarialReviewer | None = None,
        review_store: ReviewJobStore | None = None,
    ) -> None:
        self._llm = llm
        self._publisher = publisher
        self._dedup = dedup
        self._timeout_seconds = timeout_seconds
        self._templates = templates if templates is not None else TemplateSet([])
        self._reviewer = reviewer
        self._review_store = review_store
        self._resume_pending_reviews()
        meter = metrics.get_meter("mnemo-core.pipeline")
        self._operations = meter.create_counter(
            "mnemo.pipeline.operations",
            description="Pipeline operations by outcome",
        )
        self._duration = meter.create_histogram(
            "mnemo.pipeline.duration",
            unit="s",
            description="Pipeline operation duration",
        )

    async def process(self, doc: DocumentInput) -> ProcessedDocument:
        """Classify, augment, and format a document. No commit."""
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await classify_augment_format(doc, self._llm, self._templates)
        except TimeoutError as e:
            self._record("process", "timed_out", started)
            raise ProcessingError("LLM processing timed out") from e
        except Exception:
            self._record("process", "failed", started)
            raise

        if self._dedup is not None:
            try:
                async with asyncio.timeout(self._timeout_seconds):
                    result.duplicate_candidates = await self._dedup.find_candidates(result)
            except Exception:
                logger.warning("Dedup check failed, continuing without candidates", exc_info=True)

        self._record("process", "succeeded", started)
        return result

    async def publish(
        self, doc: ProcessedDocument, *, wait_for_review: bool = True
    ) -> PublishResult:
        """Commit a processed document to Git and raise a PR."""
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await self._publisher.publish(doc)
            if self._reviewer is not None:
                review_task = self._queue_review(doc, result)
                if not wait_for_review:
                    self._record("publish", "succeeded", started)
                    return result
                # Publication has committed. Review has its own durable
                # lifecycle and must not turn a completed publish into a
                # timeout failure or be cancelled with the request.
                review = await asyncio.shield(review_task)
                result = result.model_copy(update={"review": review})
            self._record("publish", "succeeded", started)
            return result
        except TimeoutError as e:
            self._record("publish", "timed_out", started)
            raise PublishError("Publishing timed out") from e
        except Exception:
            self._record("publish", "failed", started)
            raise

    async def run(
        self, doc: DocumentInput, *, wait_for_review: bool = True
    ) -> IngestResult:
        """Full pipeline: process then publish."""
        processed = await self.process(doc)
        result = await self.publish(processed, wait_for_review=wait_for_review)
        return IngestResult(document=processed, publish=result, review=result.review)

    def _record(self, operation: str, status: str, started: float) -> None:
        attributes = {"operation": operation, "status": status}
        self._operations.add(1, attributes)
        self._duration.record(time.perf_counter() - started, attributes)

    def _queue_review(
        self, doc: ProcessedDocument, published: PublishResult
    ) -> asyncio.Task[AdversarialReviewResult]:
        if self._review_store is None:
            raise RuntimeError("Adversarial review requires a durable review store")
        self._review_store.create_review_job(doc, published)
        task = asyncio.create_task(self._run_review_job(doc, published))
        task.add_done_callback(self._log_background_review_failure)
        return task

    def _resume_pending_reviews(self) -> None:
        if self._reviewer is None or self._review_store is None:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        for job in self._review_store.list_pending_review_jobs():
            task = asyncio.create_task(
                self._run_review_job(job["document"], job["published"])
            )
            task.add_done_callback(self._log_background_review_failure)

    @staticmethod
    def _log_background_review_failure(
        task: asyncio.Task[AdversarialReviewResult],
    ) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Durable adversarial review failed: %s",
                error,
                exc_info=(type(error), error, error.__traceback__),
            )

    async def _run_review_job(
        self, doc: ProcessedDocument, published: PublishResult
    ) -> AdversarialReviewResult:
        assert self._reviewer is not None
        assert self._review_store is not None
        if not self._review_store.claim_review_job(published.pr_url):
            job = self._review_store.get_review_job(published.pr_url)
            if job is not None and job["result"] is not None:
                return job["result"]
            raise RuntimeError(f"Review job for {published.pr_url} is already running")
        try:
            result = await self._reviewer.review(doc, published)
        except BaseException as error:
            self._review_store.finish_review_job(
                published.pr_url, error=str(error)[:2_000]
            )
            raise
        self._review_store.finish_review_job(published.pr_url, result=result)
        return result
