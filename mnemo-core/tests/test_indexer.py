from mnemo_core.indexing.service import Indexer
from mnemo_core.vector.sqlite_vec import SqliteVecIndex
from tests.conftest import FakeContentSource, FakeEmbedding

DOC_A = "---\ntitle: A\n---\n## First\n\nBody one.\n\n## Second\n\nBody two.\n"
DOC_B = "---\ntitle: B\n---\nJust one section, no headings.\n"


def _indexer(tmp_path, documents):
    vector_index = SqliteVecIndex(path=str(tmp_path / "vectors.db"), dimension=4)
    embedding = FakeEmbedding(dimension=4)
    content_source = FakeContentSource(documents)
    return Indexer(vector_index, embedding, content_source), vector_index, embedding


async def test_trigger_embeds_all_chunks_of_new_documents(tmp_path):
    indexer, vector_index, embedding = _indexer(tmp_path, {"docs/a.md": DOC_A})

    result = await indexer.trigger(["docs/a.md"], ref="abc123")

    assert result.chunks == 2
    assert result.added == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert set(vector_index.content_hashes()) == {"docs/a.md#0", "docs/a.md#1"}
    assert embedding.calls == [
        ["## First\n\nBody one.", "## Second\n\nBody two."]
    ]


async def test_trigger_reembeds_only_changed_chunks(tmp_path):
    indexer, vector_index, _ = _indexer(tmp_path, {"docs/a.md": DOC_A})
    await indexer.trigger(["docs/a.md"])

    changed = "---\ntitle: A\n---\n## First\n\nBody one CHANGED.\n\n## Second\n\nBody two.\n"
    indexer._content_source.documents["docs/a.md"] = changed
    embedding = indexer._embedding

    result = await indexer.trigger(["docs/a.md"])

    assert result.chunks == 2
    assert result.updated == 1
    assert result.added == 0
    assert result.unchanged == 1
    assert embedding.calls[-1] == ["## First\n\nBody one CHANGED."]


async def test_trigger_passes_commit_sha_as_ref(tmp_path):
    indexer, _, _ = _indexer(tmp_path, {"docs/a.md": DOC_A})

    await indexer.trigger(["docs/a.md"], ref="deadbeef")

    assert indexer._content_source.fetched_refs == ["deadbeef"]


async def test_reconcile_prunes_paths_no_longer_present(tmp_path):
    indexer, vector_index, _ = _indexer(tmp_path, {"docs/a.md": DOC_A, "docs/b.md": DOC_B})
    await indexer.reconcile()
    assert set(vector_index.content_hashes()) == {"docs/a.md#0", "docs/a.md#1", "docs/b.md#0"}

    indexer._content_source.documents.pop("docs/b.md")
    result = await indexer.reconcile()

    assert result.removed == 1
    assert set(vector_index.content_hashes()) == {"docs/a.md#0", "docs/a.md#1"}


async def test_reconcile_dry_run_does_not_mutate_index(tmp_path):
    indexer, vector_index, _ = _indexer(tmp_path, {"docs/a.md": DOC_A})

    result = await indexer.reconcile(dry_run=True)

    assert result.added == 2
    assert vector_index.content_hashes() == {}


async def test_trigger_on_unchanged_document_embeds_nothing(tmp_path):
    indexer, _, embedding = _indexer(tmp_path, {"docs/a.md": DOC_A})
    await indexer.trigger(["docs/a.md"])

    result = await indexer.trigger(["docs/a.md"])

    assert result.added == 0
    assert result.updated == 0
    assert result.unchanged == 2
    assert len(embedding.calls) == 1
