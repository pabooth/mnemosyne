from ..llm.base import LLMProvider
from ..models import DocumentInput, IngestResult, ProcessedDocument, PublishResult
from .classify import classify_augment_format
from .publish import Publisher


class PipelineRunner:
    def __init__(self, llm: LLMProvider, publisher: Publisher) -> None:
        self._llm = llm
        self._publisher = publisher

    async def process(self, doc: DocumentInput) -> ProcessedDocument:
        """Classify, augment, and format a document. No commit."""
        return await classify_augment_format(doc, self._llm)

    async def publish(self, doc: ProcessedDocument) -> PublishResult:
        """Commit a processed document to Git and raise a PR."""
        return await self._publisher.publish(doc)

    async def run(self, doc: DocumentInput) -> IngestResult:
        """Full pipeline: process then publish."""
        processed = await self.process(doc)
        result = await self.publish(processed)
        return IngestResult(document=processed, publish=result)
