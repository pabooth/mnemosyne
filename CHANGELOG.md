# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pull request and push CI for core, UI, containers, and Compose validation
- Docker Compose deployment with reverse proxy and optional observability stack
- Release archives, Python packages, container publishing, and `.deb`/`.rpm` packaging
- Deterministic publishing of human-edited previews without rerunning the LLM
- Input/output validation, request limits, timeouts, readiness checks, and structured logs
- OpenTelemetry metrics and traces with Prometheus/Grafana reference configuration
- Durable SQLite jobs, retries, cancellation, submission history, named token roles, and audit events
- Signed GitHub webhook intake, batch jobs, uploads, allow-listed URLs, and GitHub file sources
- Knowledge-base self-audit for staleness, ownership, duplicate titles, and broken relative links
- Deployment, configuration, MCP, provider, contribution, and security documentation

### Changed
- GitHub publishing is idempotent for identical reviewed documents and safely handles existing branches/files
- Browser API tokens now use session storage instead of persistent local storage
- The UI defaults to live API mode and supports editing previews before submission

### Fixed
- Invalid `mnemo-ui/package.json` that prevented UI tests and builds
- Python source distributions accidentally including local virtual environments

## [0.1.0] - 2026-06-18

### Added
- Initial release
- MCP intake interface for document ingestion
- Human-in-the-loop review pipeline via GitHub PRs
- Web UI (mnemo-ui) and backend engine (mnemo-core)
