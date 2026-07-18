# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Adversarial adjudication (ADR-020): the processing model now supplies an
  acceptance case, a cross-family critic challenges it, and a third-family
  judge accepts, rejects, or escalates Tier 1 proposals and recommends accept
  or reject for mandatory-human-review Tier 2 proposals.

### Changed

- Adversarial-review configuration is intentionally breaking:
  `REVIEWER_ADVOCATE_PROVIDER` and `REVIEWER_ADVOCATE_MODEL` are removed;
  deployments enabling review must add `REVIEWER_JUDGE_PROVIDER` and
  `REVIEWER_JUDGE_MODEL`, and main, critic, and judge providers must all differ.

- KB-owned document templates (ADR-018): templates live in the knowledge
  base's `templates/<type>/<sub-label>.md` files and are fetched once at
  startup; the template set defines the sub-label taxonomy, so adding a
  document type is a PR to the KB, not a Mnemosyne release. A template's
  frontmatter `description` feeds the classifier prompt verbatim. Starter
  templates live in `examples/templates/`; the previously built-in
  "standard" template moved there, and Mnemosyne now ships none embedded.
  Template fetch failures are fatal at startup by design; template files
  are excluded from indexing and curator scans.

## [2.1.0] - 2026-07-13
Multiple changes made to config and runtime issues


### Added

- Standalone `mnemo-proxy` component and versioned container image for routing
  UI, REST, MCP, and health traffic, replacing the deployment-mounted proxy
  configuration (ADR-016).
- Pluggable vector-index layer (ADR-014) with `sqlite-vec` as the embedded
  reference implementation, in its own SQLite file by default
  (`VECTOR_DB_PATH=""` opts in to sharing the durable-job file).
- Pluggable embedding provider (`EMBEDDING_PROVIDER`: `openai` or `ollama`),
  independent from `LLM_PROVIDER` since Anthropic and DeepSeek don't offer
  an embeddings API.
- `POST /api/v1/index/trigger` and `POST /api/v1/index/reconcile` now embed
  and index Markdown content instead of failing as contract stubs:
  `trigger` embeds specific paths on demand; `reconcile` diffs the full
  repo against the vector index by content hash and processes only what
  changed.
- Read-path dedup check (`DEDUP_ENABLED`, off by default): `process` and
  `ingest` can check the vector index for likely-existing duplicates before
  returning. Matches never block the pipeline — they're attached to the
  result as `duplicate_candidates` and noted in the PR body for the human
  reviewer to weigh.

### Changed

- Docker Compose now starts only required `mnemo-core` by default. The
  optional browser stack (`mnemo-ui` and `mnemo-proxy`) requires the `ui`
  profile; curator and observability retain their existing profiles.
- Persistence layout (ADR-015): data moved from anonymous named Docker
  volumes to bind-mounted, per-component directories, with all SQLite
  stores opened in WAL mode.
- Instance directory (ADR-017): all instance state — configuration and
  data — now lives in one directory located by `MNEMO_HOME`
  (conventionally `~/mnemosyne` for development, `/srv/mnemosyne` on a
  Linux server), holding `mnemosyne.env` and `data/<component>/`. Docker
  Compose fails loudly when `MNEMO_HOME` is unset; the `./data` fallback,
  checkout-root `.env` auto-discovery, and the `MNEMO_DATA_DIR` variable
  are removed. `.env.example` is renamed `mnemosyne.env.example`.
- Databases renamed by function (ADR-017): `mnemosyne.db` → `state.db`,
  `mnemo-curator-issues.db` → `issues.db` (`vectors.db` unchanged), each
  matching its configuration variable. Existing deployments must migrate —
  see "Migrating from earlier data layouts" in
  `docs/deployment/docker-compose.md`.

### Removed

- The `.deb`/`.rpm` packages. They wrapped Docker Compose rather than
  installing Mnemosyne natively, which added a second deployment surface
  without the guarantees of OS packaging (upgrades, rollbacks, and
  uninstalls all bypassed the package manager). Deployment is Docker
  Compose from a checkout, or the published GHCR images with your own
  Compose file. A native package that installs the Python applications
  directly may return in future.

## [2.0.0] - 2026-07-07



### Added

- URI-path API versioning per ADR-013: all content endpoints now live under
  `/api/v1`, served from the self-contained `mnemo_core/api/v1` router
  package. `/health` and `/ready` remain unversioned.
- Contract-stub indexer endpoints `POST /api/v1/index/trigger` and
  `POST /api/v1/index/reconcile`; both queue durable jobs that fail
  immediately until indexing logic is implemented.
- `mnemo-curator`, an optional knowledge-base inspection and resolution
  service with internal Inspector and Resolver components. It records findings
  through GitHub, Jira, or SQLite issue trackers, applies safe structural
  fixes, optionally performs OpenAI-compatible semantic rewrites, and submits fixes through
  `mnemo-core`'s `/api/v1/ingest` path.

### Changed

- Durable jobs accept any Pydantic payload and support the new
  `index_trigger`/`index_reconcile` job kinds; `NotImplementedError` marks a
  job failed immediately instead of retrying.

### Removed

- Knowledge-base self-audit (`mnemo_core/self_audit.py`,
  `POST /api/audit/knowledge-base`, and the `AUDIT_STALE_AFTER_DAYS` /
  `AUDIT_MAX_FILES` settings). Inspection and resolution now live in
  `mnemo-curator` per ADR-012. The job audit trail (`GET /api/v1/audit`)
  remains.

## [1.1.0] - 2026-06-21
Security and project artifact improvements
Documentation fixes
CLI command versioning
Build and testing changes


### Added

- Configurable host bindings and core-container runtime UID/GID settings.
- Package metadata, README, and license files for standalone `mnemo-core`
  distributions.
- Version reporting for `mnemo-evaluate` and packaged `mnemosyne` commands.
- Bug report, feature request, and pull request templates.
- Code of conduct, support policy, and maintainer release documentation.
- Wheel and source-distribution installation smoke tests in CI and release
  workflows.

### Changed

- FastAPI now reports the installed `mnemo-core` package version.
- Release archives now contain tracked source files and freshly built UI
  assets rather than local build debris.
- Release automation now verifies tag, manifest, lockfile, and changelog
  version consistency.
- Direct core and observability ports default to loopback, while host bindings
  remain configurable.
- OpenTelemetry collector ports are available only on the internal Compose
  network.
- Grafana no longer defaults to the `admin` password and user sign-up is
  disabled.
- Security and contribution documentation now use consistent project
  policies.

### Fixed

- Synchronized the UI package lockfile with the current project version.

## [1.0.2] - 2026-06-21

### Changed

- Updated CodeRabbit auto-review tooling.

## [1.0.1] - 2026-06-20

### Changed

- Corrected the build-system configuration.

## [1.0.0] - 2026-06-20

### Added

- Pull request and push CI for core, UI, containers, and Compose validation.
- Docker Compose deployment with reverse proxy and optional observability
  stack.
- Release archives, Python packages, container publishing, and `.deb`/`.rpm`
  packaging.
- Deterministic publishing of human-edited previews without rerunning the LLM.
- Input/output validation, request limits, timeouts, readiness checks, and
  structured logs.
- OpenTelemetry metrics and traces with Prometheus/Grafana reference
  configuration.
- Durable SQLite jobs, retries, cancellation, submission history, named token
  roles, and audit events.
- Signed GitHub webhook intake, batch jobs, uploads, allow-listed URLs, and
  GitHub file sources.
- Knowledge-base self-audit for staleness, ownership, duplicate titles, and
  broken relative links.
- Deployment, configuration, MCP, provider, contribution, and security
  documentation.

### Changed

- GitHub publishing is idempotent for identical reviewed documents and safely
  handles existing branches/files.
- Browser API tokens now use session storage instead of persistent local
  storage.
- The UI defaults to live API mode and supports editing previews before
  submission.

### Fixed

- Invalid `mnemo-ui/package.json` that prevented UI tests and builds.
- Python source distributions accidentally including local virtual
  environments.

## [0.1.0] - 2026-06-18

### Added

- Initial release.
- MCP intake interface for document ingestion.
- Human-in-the-loop review pipeline via GitHub PRs.
- Web UI (`mnemo-ui`) and backend engine (`mnemo-core`).

[Unreleased]: https://github.com/pabooth/mnemosyne/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/pabooth/mnemosyne/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/pabooth/mnemosyne/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/pabooth/mnemosyne/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/pabooth/mnemosyne/releases/tag/v0.1.0
