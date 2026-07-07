# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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
