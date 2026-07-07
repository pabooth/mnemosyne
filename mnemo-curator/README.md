# mnemo-curator

`mnemo-curator` is the Mnemosyne knowledge-base inspection and resolution
service.

It contains two internal components:

- Inspector: scans Git-backed Markdown content for structural findings and
  semantic quality gaps.
- Resolver: records each finding through the configured issue tracker, applies
  safe structural fixes deterministically, optionally asks an
  OpenAI-compatible model for semantic rewrites, and submits corrected content
  through `mnemo-core`'s normal `/api/v1/ingest` path.

`mnemo-curator` is separate from `mnemo-core` by design. `mnemo-core` remains
the governed ingestion and publishing boundary; curator fixes still become
pull requests through core.

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -q
```

## Configuration

| Variable | Purpose |
|---|---|
| `GITHUB_TOKEN` | Token used to read repository contents; also used for GitHub issue tracking |
| `GITHUB_REPO` | Target repository in `owner/repository` form |
| `DOCS_ROOT` | Optional Markdown root within the repository |
| `MNEMO_CORE_URL` | Base URL for `mnemo-core`, default `http://localhost:7777` |
| `MNEMO_API_TOKEN` | Bearer token used when submitting fixes to core |
| `CURATOR_STALE_AFTER_DAYS` | Review staleness threshold, default `180` |
| `CURATOR_MAX_FILES` | Maximum Markdown files per scan, default `500` |
| `CURATOR_DEFAULT_OWNER` | Owner inserted by safe structural fixes, default `unset` |
| `CURATOR_ISSUE_TRACKER` | `github`, `jira`, or `sqlite`; default `github` |
| `CURATOR_ISSUE_LABELS` | Comma-separated labels for recorded findings |
| `CURATOR_ISSUE_DB_PATH` | SQLite issue store path when using `sqlite` |
| `CURATOR_SEMANTIC_RESOLUTION_ENABLED` | Enables model-assisted semantic rewrites |
| `JIRA_BASE_URL` | Jira site URL when using `jira` |
| `JIRA_EMAIL` | Jira account email when using `jira` |
| `JIRA_API_TOKEN` | Jira API token when using `jira` |
| `JIRA_PROJECT_KEY` | Jira project key when using `jira` |
| `JIRA_ISSUE_TYPE` | Jira issue type, default `Task` |
| `OPENAI_API_KEY` | API key for an OpenAI-compatible model endpoint |
| `OPENAI_BASE_URL` | OpenAI-compatible base URL |
| `OPENAI_MODEL` | Model used for semantic rewrites |

## CLI

```bash
mnemo-curator scan
mnemo-curator scan --resolve
```

`scan` records findings through the configured issue tracker. `--resolve` also
attempts inline resolution after issue creation.
