# AGENTS.md

Guidance for AI coding agents working in this repository. Keep this file
agent-neutral: it should describe project invariants, local workflows, and
where to find source-of-truth context.

## Project invariants

Mnemosyne is an AI-assisted document ingestion engine. It classifies source
material with the Diataxis framework, improves structure and metadata, and
opens a pull request for human review.

Generated content must never be merged automatically. All paths that publish
content must create a branch and pull request for human review. This is a hard
governance requirement, not a configuration option.

Diataxis document type and review tier are separate axes:

- Diataxis controls document shape: tutorial, how-to, reference, explanation.
- Review tier controls review depth and risk handling.

## Source of truth

Read the relevant ADR before changing architecture, API contracts, governance,
deployment boundaries, MCP behavior, or review policy. ADRs live in
`docs/ADRs/`; new ADRs should use `docs/ADRs/TEMPLATE.md`.

Key ADRs:

- ADR-005: mandatory human review before content reaches the knowledge base.
- ADR-006 and ADR-008: MCP is an intake interface only.
- ADR-011: review tier model.
- ADR-012: deployment boundaries and service ownership.
- ADR-013: API contract-first design and URI-path versioning.

## Current architecture

- `mnemo-core` is required. It owns the REST API, MCP server, processing
  pipeline, durable jobs, GitHub publishing, webhook intake, and indexer
  contract stubs.
- `mnemo-ui` is optional. It is a static browser UI for previewing, editing,
  submitting documents, and viewing job history.
- `mnemo-curator` is optional. It owns knowledge-base inspection and
  resolution through internal Inspector and Resolver components.
- `mnemo-bot` is optional and not yet built.

The knowledge base itself is outside Mnemosyne. Mnemosyne feeds a Git-backed
content store; another system serves that content.

## API contract

The REST API is versioned under `/api/v1`. `/health` and `/ready` are the only
unversioned routes. Once an API version is superseded, freeze it except for
bug fixes; behavior changes belong in the next version.

New API endpoints should be added contract-first: define route signatures and
Pydantic request/response models before implementing business logic.

Current v1 facts:

- `mnemo_core/api/v1/` contains the versioned routers.
- `GET /api/v1/audit` is the job audit trail.
- `POST /api/v1/index/trigger` and `POST /api/v1/index/reconcile` are contract
  stubs that queue durable jobs and currently fail immediately.
- Knowledge-base self-audit and `POST /api/audit/knowledge-base` have been
  removed from `mnemo-core`.

Bearer-token REST routes use `Authorization: Bearer <token>`. GitHub webhooks
use `X-Hub-Signature-256` instead.

## Repo workflow

Do not revert or overwrite existing user changes. The working tree may be
dirty; inspect status before editing and keep changes scoped.

Prefer existing patterns and shared plumbing:

- API dependencies: `mnemo_core/api/deps.py`
- API auth: `mnemo_core/api/auth.py`
- Durable jobs: `mnemo_core/jobs.py`
- Pipeline runner: `mnemo_core/pipeline/runner.py`

Use fast local search (`rg`, `rg --files`) before broad edits.

## Checks

Core:

```bash
cd mnemo-core
.venv/bin/pytest -q
.venv/bin/ruff check mnemo_core tests
```

UI:

```bash
cd mnemo-ui
npm test
npm run build
```

Compose:

```bash
docker compose config
```

Curator:

```bash
cd mnemo-curator
.venv/bin/pytest -q
.venv/bin/ruff check mnemo_curator tests
```

Run the smallest relevant check for the change. If a check cannot be run,
state that clearly in the final response.
