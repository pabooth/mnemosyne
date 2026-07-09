from mnemo_core.pipeline.dedup import DuplicateChecker
from mnemo_core.vector.base import VectorRecord
from mnemo_core.vector.sqlite_vec import SqliteVecIndex
from tests.conftest import FakeEmbedding, processed_doc


def _checker(tmp_path, *, max_distance=0.35, top_k=3):
    vector_index = SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=4)
    embedding = FakeEmbedding(dimension=4)
    return DuplicateChecker(vector_index, embedding, max_distance=max_distance, top_k=top_k), vector_index


async def test_find_candidates_returns_empty_when_index_is_empty(tmp_path):
    checker, _ = _checker(tmp_path)

    candidates = await checker.find_candidates(processed_doc())

    assert candidates == []


async def test_find_candidates_returns_match_within_threshold(tmp_path):
    checker, vector_index = _checker(tmp_path, max_distance=100.0)
    vector_index.upsert(
        [
            VectorRecord(
                id="how-to/deploy.md#0",
                content_hash="hash-a",
                embedding=[0.0, 0.0, 0.0, 0.0],
                metadata={"path": "how-to/deploy.md"},
            )
        ]
    )

    candidates = await checker.find_candidates(processed_doc())

    assert len(candidates) == 1
    assert candidates[0].path == "how-to/deploy.md"


async def test_find_candidates_excludes_matches_beyond_threshold(tmp_path):
    checker, vector_index = _checker(tmp_path, max_distance=0.0001)
    vector_index.upsert(
        [
            VectorRecord(
                id="how-to/deploy.md#0",
                content_hash="hash-a",
                embedding=[5.0, 5.0, 5.0, 5.0],
                metadata={"path": "how-to/deploy.md"},
            )
        ]
    )

    candidates = await checker.find_candidates(processed_doc())

    assert candidates == []


async def test_find_candidates_collapses_multiple_chunk_hits_to_best_score_per_path(tmp_path):
    checker, vector_index = _checker(tmp_path, max_distance=100.0)
    vector_index.upsert(
        [
            VectorRecord(
                id="how-to/deploy.md#0",
                content_hash="hash-a",
                embedding=[0.0, 0.0, 0.0, 0.0],
                metadata={"path": "how-to/deploy.md"},
            ),
            VectorRecord(
                id="how-to/deploy.md#1",
                content_hash="hash-b",
                embedding=[1.0, 0.0, 0.0, 0.0],
                metadata={"path": "how-to/deploy.md"},
            ),
        ]
    )

    candidates = await checker.find_candidates(
        processed_doc(body="## First\n\nBody one.\n\n## Second\n\nBody two.")
    )

    assert len(candidates) == 1
    assert candidates[0].path == "how-to/deploy.md"


async def test_find_candidates_respects_top_k(tmp_path):
    checker, vector_index = _checker(tmp_path, max_distance=100.0, top_k=1)
    vector_index.upsert(
        [
            VectorRecord(
                id="a.md#0",
                content_hash="hash-a",
                embedding=[0.0, 0.0, 0.0, 0.0],
                metadata={"path": "a.md"},
            ),
            VectorRecord(
                id="b.md#0",
                content_hash="hash-b",
                embedding=[1.0, 0.0, 0.0, 0.0],
                metadata={"path": "b.md"},
            ),
        ]
    )

    candidates = await checker.find_candidates(processed_doc())

    assert len(candidates) == 1
