from mnemo_curator.frontmatter import set_frontmatter_value


def test_set_frontmatter_value_creates_frontmatter_when_none_exists():
    result = set_frontmatter_value("Body text", "owner", "platform")

    assert result == "---\nowner: platform\n---\n\nBody text"


def test_set_frontmatter_value_replaces_existing_key():
    content = "---\ntitle: A\nowner: unset\n---\n\nBody"

    result = set_frontmatter_value(content, "owner", "platform")

    assert "owner: platform" in result
    assert "owner: unset" not in result
    assert result.count("owner:") == 1


def test_set_frontmatter_value_appends_missing_key():
    content = "---\ntitle: A\n---\n\nBody"

    result = set_frontmatter_value(content, "owner", "platform")

    assert "title: A" in result
    assert "owner: platform" in result


def test_set_frontmatter_value_preserves_body_after_frontmatter():
    content = "---\ntitle: A\n---\n\nFirst line.\nSecond line.\n"

    result = set_frontmatter_value(content, "owner", "platform")

    assert result.endswith("First line.\nSecond line.\n")
