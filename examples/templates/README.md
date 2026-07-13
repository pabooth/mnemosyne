# Example document templates

Mnemosyne ships no built-in templates: your knowledge base's `templates/`
directory is the whole truth about which document sub-types exist and what
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

Guard the directory with branch protection and a CODEOWNERS rule:

```
/templates/  @your-kb-maintainers
```

mnemo-core reads the template set once at startup; restart it after
merging template changes.
