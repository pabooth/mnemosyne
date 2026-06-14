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
    assert 'title: "A "quoted" title"' in md
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
    plan = build_publish_plan(doc, "acme/kb", today=date(2026, 6, 14))
    assert plan.file_path == "kb/docs/reference/security-standard.md"
    assert plan.branch == "mnemo/reference/security-standard-2026-06-14"
    assert plan.repo == "acme/kb"
