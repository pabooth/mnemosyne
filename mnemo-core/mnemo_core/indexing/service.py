from typing import Protocol

from ..embeddings.base import EmbeddingProvider
from ..models import IndexResult
from ..vector.base import VectorIndex, VectorRecord
from .chunk import chunk_markdown, content_hash


class ContentSource(Protocol):
    async def fetch(self, path: str, ref: str = "") -> str: ...
    async def list_documents(self) -> list[tuple[str, str]]: ...


class Indexer:
    """Embed-and-write logic folded into mnemo-core per ADR-012.

    Stateless per call: every run re-derives chunk ids and content hashes
    from the source content it's given, diffs them against what the vector
    index already holds, and only embeds what changed.
    """

    def __init__(
        self,
        vector_index: VectorIndex,
        embedding: EmbeddingProvider,
        content_source: ContentSource,
    ) -> None:
        self._vector_index = vector_index
        self._embedding = embedding
        self._content_source = content_source

    async def trigger(self, paths: list[str], ref: str = "") -> IndexResult:
        """On-demand path: index the specific paths that just changed."""
        documents = [(path, await self._content_source.fetch(path, ref)) for path in paths]
        return await self._apply(documents, prune_missing=False)

    async def reconcile(self, dry_run: bool = False) -> IndexResult:
        """Fallback path: diff the full repo against the vector index."""
        documents = await self._content_source.list_documents()
        return await self._apply(documents, prune_missing=True, dry_run=dry_run)

    async def _apply(
        self,
        documents: list[tuple[str, str]],
        *,
        prune_missing: bool,
        dry_run: bool = False,
    ) -> IndexResult:
        existing = self._vector_index.content_hashes()
        current: dict[str, str] = {}
        pending_ids: list[str] = []
        pending_texts: list[str] = []

        for path, content in documents:
            for i, chunk in enumerate(chunk_markdown(content)):
                chunk_id = f"{path}#{i}"
                chunk_hash = content_hash(chunk)
                current[chunk_id] = chunk_hash
                if existing.get(chunk_id) != chunk_hash:
                    pending_ids.append(chunk_id)
                    pending_texts.append(chunk)

        stale = set(existing) - set(current) if prune_missing else set()
        updated = sum(1 for chunk_id in pending_ids if chunk_id in existing)
        result = IndexResult(
            chunks=len(current),
            added=len(pending_ids) - updated,
            updated=updated,
            removed=len(stale),
            unchanged=len(current) - len(pending_ids),
        )
        if dry_run:
            return result

        if pending_texts:
            embeddings = await self._embedding.embed(pending_texts)
            records = [
                VectorRecord(
                    id=chunk_id,
                    content_hash=current[chunk_id],
                    embedding=embedding,
                    metadata={"path": chunk_id.rsplit("#", 1)[0]},
                )
                for chunk_id, embedding in zip(pending_ids, embeddings, strict=True)
            ]
            self._vector_index.upsert(records)
        if stale:
            self._vector_index.delete(list(stale))

        return result
