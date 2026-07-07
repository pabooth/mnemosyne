from mnemo_curator.inspector import Inspector
from mnemo_curator.models import Document
from mnemo_curator.settings import Settings


def test_inspector_detects_structural_findings():
    documents = [
        Document(
            path="docs/a.md",
            content="---\ntitle: Shared\nlast_reviewed: 2020-01-01\n---\n\nSee [missing](missing.md).",
        ),
        Document(
            path="docs/b.md",
            content="---\ntitle: Shared\nowner: team\nlast_reviewed: not-a-date\n---\n\nBody",
        ),
    ]

    findings = Inspector(Settings(curator_stale_after_days=30)).inspect(documents)
    kinds = [finding.kind for finding in findings]

    assert "missing-owner" in kinds
    assert "stale" in kinds
    assert "invalid-review-date" in kinds
    assert "broken-relative-link" in kinds
    assert "duplicate-title" in kinds


def test_inspector_detects_semantic_placeholders():
    documents = [
        Document(
            path="docs/a.md",
            content="---\ntitle: A\nowner: team\nlast_reviewed: 2026-01-01\n---\n\n## Next\n\nTODO",
        )
    ]

    findings = Inspector(Settings()).inspect(documents)

    assert any(finding.kind == "semantic-gap" for finding in findings)
