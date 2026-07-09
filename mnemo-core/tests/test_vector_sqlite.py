import pytest

from mnemo_core.vector.base import VectorRecord
from mnemo_core.vector.sqlite_vec import SqliteVecIndex


def _index(tmp_path, dimension=4):
    return SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=dimension)


def test_upsert_and_search_returns_closest_first(tmp_path):
    index = _index(tmp_path)
    index.upsert(
        [
            VectorRecord(
                id="a",
                content_hash="hash-a",
                embedding=[1.0, 0.0, 0.0, 0.0],
                metadata={"path": "docs/a.md"},
            ),
            VectorRecord(
                id="b",
                content_hash="hash-b",
                embedding=[0.0, 1.0, 0.0, 0.0],
                metadata={"path": "docs/b.md"},
            ),
        ]
    )

    matches = index.search([0.9, 0.1, 0.0, 0.0], top_k=2)

    assert [match.id for match in matches] == ["a", "b"]
    assert matches[0].metadata == {"path": "docs/a.md"}


def test_upsert_replaces_existing_id(tmp_path):
    index = _index(tmp_path)
    index.upsert([VectorRecord(id="a", content_hash="v1", embedding=[1.0, 0.0, 0.0, 0.0])])
    index.upsert([VectorRecord(id="a", content_hash="v2", embedding=[0.0, 1.0, 0.0, 0.0])])

    assert index.content_hashes() == {"a": "v2"}
    matches = index.search([0.0, 1.0, 0.0, 0.0], top_k=1)
    assert matches[0].id == "a"


def test_delete_removes_record(tmp_path):
    index = _index(tmp_path)
    index.upsert([VectorRecord(id="a", content_hash="hash-a", embedding=[1.0, 0.0, 0.0, 0.0])])

    index.delete(["a"])

    assert index.content_hashes() == {}


def test_delete_ignores_unknown_ids(tmp_path):
    index = _index(tmp_path)
    index.delete(["does-not-exist"])
    assert index.content_hashes() == {}


def test_content_hashes_supports_reconciliation(tmp_path):
    index = _index(tmp_path)
    index.upsert(
        [
            VectorRecord(id="a", content_hash="hash-a", embedding=[1.0, 0.0, 0.0, 0.0]),
            VectorRecord(id="b", content_hash="hash-b", embedding=[0.0, 1.0, 0.0, 0.0]),
        ]
    )

    assert index.content_hashes() == {"a": "hash-a", "b": "hash-b"}


def test_upsert_rejects_dimension_mismatch(tmp_path):
    index = _index(tmp_path)
    with pytest.raises(ValueError, match="expected 4"):
        index.upsert([VectorRecord(id="a", content_hash="hash-a", embedding=[1.0, 0.0])])


def test_search_rejects_dimension_mismatch(tmp_path):
    index = _index(tmp_path)
    with pytest.raises(ValueError, match="expected 4"):
        index.search([1.0, 0.0])


def test_reuses_same_sqlite_file_across_instances(tmp_path):
    path = str(tmp_path / "shared.db")
    SqliteVecIndex(path=path, dimension=4).upsert(
        [VectorRecord(id="a", content_hash="hash-a", embedding=[1.0, 0.0, 0.0, 0.0])]
    )

    reopened = SqliteVecIndex(path=path, dimension=4)

    assert reopened.content_hashes() == {"a": "hash-a"}
