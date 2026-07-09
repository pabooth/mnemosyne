from ..embeddings.base import EmbeddingProvider
from ..indexing.chunk import chunk_markdown
from ..models import DuplicateCandidate, ProcessedDocument
from ..vector.base import VectorIndex
from .markdown import build_markdown


class DuplicateChecker:
    """Read-path KB query: surfaces likely-duplicate existing content.

    Never blocks ingestion — matches are attached to the ProcessedDocument
    for a human reviewer to weigh in the PR, consistent with the project's
    human-review governance (ADR-005/ADR-011). Chunks the candidate the
    same way the indexer chunks published content (chunk_markdown over the
    built markdown) so both sides of the comparison are the same
    granularity.
    """

    def __init__(
        self,
        vector_index: VectorIndex,
        embedding: EmbeddingProvider,
        *,
        max_distance: float,
        top_k: int = 3,
    ) -> None:
        self._vector_index = vector_index
        self._embedding = embedding
        self._max_distance = max_distance
        self._top_k = top_k

    async def find_candidates(self, doc: ProcessedDocument) -> list[DuplicateCandidate]:
        chunks = chunk_markdown(build_markdown(doc))
        if not chunks:
            return []

        embeddings = await self._embedding.embed(chunks)

        best_by_path: dict[str, float] = {}
        for embedding in embeddings:
            for match in self._vector_index.search(embedding, top_k=self._top_k):
                if match.score > self._max_distance:
                    continue
                path = match.metadata.get("path", match.id)
                if path not in best_by_path or match.score < best_by_path[path]:
                    best_by_path[path] = match.score

        candidates = [
            DuplicateCandidate(path=path, score=score) for path, score in best_by_path.items()
        ]
        candidates.sort(key=lambda candidate: candidate.score)
        return candidates[: self._top_k]
