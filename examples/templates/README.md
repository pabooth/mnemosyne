# Example document templates

Mnemosyne ships no built-in templates: your knowledge base's `templates/`
directory is the whole truth about which document subtypes exist and what
they contain (ADR-018). These examples are starting points — copy the ones
you want into your KB and edit them to match your conventions:

```bash
cp -R examples/templates/{tutorials,how-to,reference,explanation} <your-kb>/templates/
```

Each template is `templates/<type-folder>/<sub-label>.md`, where the folder
is one of the Diataxis content folders (`tutorials`, `how-to`, `reference`,
`explanation`) and the filename becomes the sub-label. The frontmatter
carries two fields:

- `description` — read by the classifier verbatim; it is the definition of
  when a document counts as this type, so write it as carefully as the
  template body.
- `tier` — the ADR-011 review tier for documents of this type: `tier-1`
  (may auto-merge when both adversarial reviewers accept) or `tier-2`
  (human approval always required). A missing `tier` fails closed to
  `tier-2`. Declaring `tier-1` is a positive editorial decision to open
  the auto-merge path for that document type — the example set marks
  normative types (standard, principle, sop, requirements, strategy, adr,
  rfc) as `tier-2` and descriptive/factual types as `tier-1`.

Guard the directory with the KB's existing branch protection (pull
requests only, passing checks, at least one human approval, and the
Mnemosyne service account unable to merge) plus a CODEOWNERS rule:

```text
/templates/  @your-kb-maintainers
```

Because template changes require human approval and the service account
cannot merge them, the template set satisfies ADR-011's requirement that
the definition of tier membership is itself Tier 2 content.

mnemo-core reads the template set once at startup; restart it after
merging template changes.
