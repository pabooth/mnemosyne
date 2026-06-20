# Knowledge-base providers

Mnemosyne writes standard Markdown with YAML frontmatter. `DOCS_ROOT` selects
the root directory and Diátaxis types are written beneath it.

## MkDocs Material

Set `DOCS_ROOT=docs`. The generated folders can be included in `nav` manually
or discovered by an MkDocs navigation plugin.

## Docusaurus

Set `DOCS_ROOT=docs`. Docusaurus accepts the generated Markdown, but projects
using MDX should review text containing JSX-like syntax before merging.

## VitePress

Set `DOCS_ROOT=docs`. Add the Diátaxis folders to the VitePress sidebar
configuration.

## Obsidian

Target a Git repository containing the vault. Set `DOCS_ROOT` to the desired
vault folder. Generated YAML frontmatter is compatible with Obsidian
properties.

## Plain GitHub

Leave `DOCS_ROOT` empty or choose a documentation folder. Markdown and
frontmatter remain readable through GitHub's renderer.

## SharePoint

SharePoint is not a native Git/Markdown target. Use an external synchronization
workflow after merge to convert or publish Markdown into SharePoint pages.
Mnemosyne does not bypass that platform-specific conversion step.
