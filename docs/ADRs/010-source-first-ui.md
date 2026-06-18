# ADR-010: Maintain mnemo-ui as source modules, not a monolithic HTML bundle

> **Status:** `Accepted`
> **Date:** 2026-06-16
> **Review date:** 2027-06-16

---

## Context

The initial `mnemo-ui` artifact was a generated single-file `index.html` containing bootstrap code, application logic, markup, styles, and embedded assets. That format is convenient for demos, but it is not suitable as the primary source of a public-facing interface.

Problems with the monolithic artifact included difficult code review, weak test boundaries, awkward security hardening, and high risk when changing small UI behaviours.

## Decision

Use a source-first static frontend layout:

- `index.html` is a small entry point.
- `src/` contains separate modules for configuration, API access, state, rendering, Markdown handling, storage, and security helpers.
- `public/` contains static visual assets.
- `scripts/build.mjs` produces `dist/` without requiring third-party dependencies.
- Tests cover source structure, pure helper behaviour, and build output.

The UI remains framework-free for now because the current scope is small and no dependency installation is required to build or test it. If the UI grows materially, a conventional Vite application with component tests should be reconsidered.

## Consequences

The application is easier to review and evolve on the way to public release. Security-sensitive logic such as URL validation, output escaping, and Markdown rendering now has explicit module boundaries.

The renderer is still a lightweight template-string implementation. It must continue escaping all state and API response values before insertion into `innerHTML`; richer interaction or larger UI surfaces should trigger a move to component rendering with stronger default escaping.
