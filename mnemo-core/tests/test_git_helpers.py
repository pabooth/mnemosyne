from datetime import date

import pytest

from mnemo_core.pipeline.markdown import build_markdown, slugify
from mnemo_core.pipeline.publish import build_publish_plan
from tests.conftest import processed_doc


def test_slugify_strips_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_collapses_whitespace():
    assert slugify("foo   bar_baz") == "foo-bar-baz"


def test_build_markdown_includes_frontmatter():
    doc = processed_doc(title='A "quoted" title')
    md = build_markdown(doc)
    assert 'title: "A \\"quoted\\" title"' in md
    assert "type: how-to" in md
    assert "tags:" in md
    assert "  - deploy" in md
    assert "## Steps" in md


def test_build_markdown_omits_empty_sub_label():
    doc = processed_doc(sub_label="")
    md = build_markdown(doc)
    assert "sub_label:" not in md


def test_build_publish_plan_reference_folder():
    doc = processed_doc(type="reference", title="Security Standard")
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14), branch_suffix="abc123")
    assert plan.file_path == "reference/security-standard.md"
    assert plan.branch == "mnemo/reference/security-standard-2026-06-14-abc123"
    assert plan.repo == "acme/kb"


def test_build_publish_plan_branch_suffix_is_idempotent_for_same_document():
    doc = processed_doc(type="reference", title="Security Standard")
    plan_a = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))
    plan_b = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))
    assert plan_a.branch == plan_b.branch


def test_build_publish_plan_branch_suffix_changes_with_document():
    plan_a = build_publish_plan(
        processed_doc(type="reference", title="Security Standard"),
        "acme/kb",
        today=date(2026, 6, 14),
    )
    plan_b = build_publish_plan(
        processed_doc(type="reference", title="Security Standard", body="Changed body"),
        "acme/kb",
        today=date(2026, 6, 14),
    )
    assert plan_a.branch != plan_b.branch


def test_build_publish_plan_with_docs_root():
    doc = processed_doc(type="reference", title="Security Standard")
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14), docs_root="kb/docs", branch_suffix="x")
    assert plan.file_path == "kb/docs/reference/security-standard.md"


def test_build_publish_plan_docs_root_strips_slashes():
    doc = processed_doc(type="how-to", title="Deploy the app")
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14), docs_root="/kb/docs/", branch_suffix="x")
    assert plan.file_path == "kb/docs/how-to/deploy-the-app.md"


def test_build_publish_plan_rejects_path_traversal():
    with pytest.raises(Exception, match="unsafe path"):
        build_publish_plan(processed_doc(), "acme/kb", docs_root="../../tmp")


def test_build_markdown_quotes_special_char_tags():
    doc = processed_doc(tags=["safe-tag", "needs: quoting", "also#quoted"])
    md = build_markdown(doc)
    assert '  - safe-tag' in md
    assert '  - "needs: quoting"' in md
    assert '  - "also#quoted"' in md


def test_build_markdown_quotes_special_char_flags():
    doc = processed_doc(flags=["needs-review", "has: colon"])
    md = build_markdown(doc)
    assert "  - needs-review" in md
    assert '  - "has: colon"' in md
