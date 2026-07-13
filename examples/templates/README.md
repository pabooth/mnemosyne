# Example document templates

Mnemosyne ships no built-in templates: your knowledge base's `templates/`
directory is the whole truth about which document subtypes exist and what
they contain (ADR-018). These examples are starting points — copy the ones
you want into your KB and edit them to match your conventions:

```bash
cp -R examples/templates/reference <your-kb>/templates/
```

Each template is `templates/<type-folder>/<sub-label>.md`, where the folder
is one of the Diataxis content folders (`tutorials`, `how-to`, `reference`,
`explanation`) and the filename becomes the sub-label. The frontmatter
`description` is read by the classifier verbatim — it is the definition of
when a document counts as this type, so write it as carefully as the
template body.

Guard the directory with the KB's existing branch protection (pull
requests only, passing checks, at least one human approval, and the
Mnemosyne service account unable to merge) plus a CODEOWNERS rule:

```text
/templates/  @your-kb-maintainers
```

mnemo-core reads the template set once at startup; restart it after
merging template changes.
