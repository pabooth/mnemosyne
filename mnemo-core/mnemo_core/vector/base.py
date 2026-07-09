from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class VectorRecord:
    """A single embedded chunk to be stored in the index.

    ``content_hash`` is what the reconciliation pass (ADR-012) diffs against
    the repo to find what's missing or stale, independent of the ``id``
    naming scheme any particular caller chooses.
    """

    id: str
    content_hash: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorMatch:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorIndex(ABC):
    """Contract for the pluggable vector-index layer (ADR-014).

    Implementations back the read-path dedup check and mnemo-bot's semantic
    search; both are the caller's concern, not this contract's.
    """

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        """Insert or replace records by id."""
        ...

    @abstractmethod
    def search(self, embedding: list[float], top_k: int = 5) -> list[VectorMatch]:
        """Return the top_k nearest records to embedding, closest first."""
        ...

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        """Remove records by id. Unknown ids are ignored."""
        ...

    @abstractmethod
    def content_hashes(self) -> dict[str, str]:
        """Return {id: content_hash} for every indexed record.

        Used by the reconciliation pass to diff "what's in the Repo at
        main" against "what's in the Vector DB" without re-embedding
        unchanged content.
        """
        ...
