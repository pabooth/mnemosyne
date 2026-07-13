import asyncio
import logging
import time

from opentelemetry import metrics

from ..llm.base import LLMProvider
from ..models import DocumentInput, IngestResult, ProcessedDocument, PublishResult
from . import ProcessingError, PublishError
from .classify import classify_augment_format
from .dedup import DuplicateChecker
from .publish import Publisher
from .templates import TemplateSet

logger = logging.getLogger(__name__)


class PipelineRunner:
    def __init__(
        self,
        llm: LLMProvider,
        publisher: Publisher,
        dedup: DuplicateChecker | None = None,
        timeout_seconds: float = 120,
        templates: TemplateSet | None = None,
    ) -> None:
        self._llm = llm
        self._publisher = publisher
        self._dedup = dedup
        self._timeout_seconds = timeout_seconds
        self._templates = templates if templates is not None else TemplateSet([])
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

    async def publish(self, doc: ProcessedDocument) -> PublishResult:
        """Commit a processed document to Git and raise a PR."""
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await self._publisher.publish(doc)
            self._record("publish", "succeeded", started)
            return result
        except TimeoutError as e:
            self._record("publish", "timed_out", started)
            raise PublishError("Publishing timed out") from e
        except Exception:
            self._record("publish", "failed", started)
            raise

    async def run(self, doc: DocumentInput) -> IngestResult:
        """Full pipeline: process then publish."""
        processed = await self.process(doc)
        result = await self.publish(processed)
        return IngestResult(document=processed, publish=result)

    def _record(self, operation: str, status: str, started: float) -> None:
        attributes = {"operation": operation, "status": status}
        self._operations.add(1, attributes)
        self._duration.record(time.perf_counter() - started, attributes)
