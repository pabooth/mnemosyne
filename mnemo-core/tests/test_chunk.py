from mnemo_core.indexing.chunk import chunk_markdown, content_hash, strip_frontmatter

FRONTMATTER = """---
title: "Deploy the app"
type: how-to
---
"""


def test_strip_frontmatter_removes_leading_block():
    content = FRONTMATTER + "## Steps\n\nDo the thing.\n"
    assert strip_frontmatter(content) == "## Steps\n\nDo the thing.\n"


def test_strip_frontmatter_is_noop_without_frontmatter():
    content = "## Steps\n\nDo the thing.\n"
    assert strip_frontmatter(content) == content


def test_chunk_markdown_splits_on_top_level_headings():
    content = FRONTMATTER + (
        "## First\n\nFirst body.\n\n"
        "## Second\n\nSecond body.\n"
    )
    chunks = chunk_markdown(content)
    assert chunks == ["## First\n\nFirst body.", "## Second\n\nSecond body."]


def test_chunk_markdown_keeps_lead_in_before_first_heading():
    content = FRONTMATTER + "Intro paragraph.\n\n## Steps\n\nDo the thing.\n"
    chunks = chunk_markdown(content)
    assert chunks == ["Intro paragraph.", "## Steps\n\nDo the thing."]


def test_chunk_markdown_returns_single_chunk_without_headings():
    content = FRONTMATTER + "Just a short explanation with no sections.\n"
    assert chunk_markdown(content) == ["Just a short explanation with no sections."]


def test_chunk_markdown_returns_empty_list_for_blank_body():
    assert chunk_markdown(FRONTMATTER) == []


def test_content_hash_is_stable_and_sensitive_to_change():
    assert content_hash("a") == content_hash("a")
    assert content_hash("a") != content_hash("b")
