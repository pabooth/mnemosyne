import json
import sqlite3
from pathlib import Path

import sqlite_vec

from .base import VectorIndex, VectorMatch, VectorRecord


class SqliteVecIndex(VectorIndex):
    """Reference vector-index implementation (ADR-014/ADR-015).

    Embedded and file-based: loads the ``sqlite-vec`` extension into a
    plain SQLite file, by default its own file separate from durable job
    storage so bulk embedding writes don't lock-contend with job status
    updates. A self-hoster gains semantic search without standing up a
    second storage subsystem or a new service.
    """

    def __init__(self, path: str, dimension: int) -> None:
        self.path = path
        self.dimension = dimension
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.enable_load_extension(True)
        sqlite_vec.load(connection)
        connection.enable_load_extension(False)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_documents USING vec0(
                    embedding float[{self.dimension}],
                    +id TEXT,
                    +content_hash TEXT,
                    +metadata_json TEXT
                )
                """
            )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        for record in records:
            if len(record.embedding) != self.dimension:
                raise ValueError(
                    f"Embedding for id={record.id!r} has dimension "
                    f"{len(record.embedding)}, expected {self.dimension}"
                )
        with self._connect() as db:
            db.executemany(
                "DELETE FROM vec_documents WHERE id = ?",
                [(record.id,) for record in records],
            )
            db.executemany(
                "INSERT INTO vec_documents (embedding, id, content_hash, metadata_json) "
                "VALUES (?, ?, ?, ?)",
                [
                    (
                        sqlite_vec.serialize_float32(record.embedding),
                        record.id,
                        record.content_hash,
                        json.dumps(record.metadata),
                    )
                    for record in records
                ],
            )

    def search(self, embedding: list[float], top_k: int = 5) -> list[VectorMatch]:
        if len(embedding) != self.dimension:
            raise ValueError(
                f"Query embedding has dimension {len(embedding)}, expected {self.dimension}"
            )
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT id, metadata_json, distance
                FROM vec_documents
                WHERE embedding MATCH ? AND k = ?
                ORDER BY distance
                """,
                (sqlite_vec.serialize_float32(embedding), top_k),
            ).fetchall()
        return [
            VectorMatch(id=row[0], score=row[2], metadata=json.loads(row[1]))
            for row in rows
        ]

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        with self._connect() as db:
            db.executemany("DELETE FROM vec_documents WHERE id = ?", [(i,) for i in ids])

    def content_hashes(self) -> dict[str, str]:
        with self._connect() as db:
            rows = db.execute("SELECT id, content_hash FROM vec_documents").fetchall()
        return {row[0]: row[1] for row in rows}
