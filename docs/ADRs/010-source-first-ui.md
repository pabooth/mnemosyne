# ADR-010: Maintain mnemo-ui as source modules, not a monolithic HTML bundle

> **Status:** `Accepted`
> **Date:** 2026-06-16
> **Review date:** 2027-06-16

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-010 |
| **Title** | Maintain mnemo-ui as source modules, not a monolithic HTML bundle |
| **Status** | Accepted |
| **Date** | 2026-06-16 |
| **Review date** | 2027-06-16 |
| **Supersedes** | — |
| **Superseded by** | — |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

The initial `mnemo-ui` artifact was a generated single-file `index.html` containing bootstrap code, application logic, markup, styles, and embedded assets. That format is convenient for demos, but it is not suitable as the primary source of a public-facing interface.

Problems with the monolithic artifact included difficult code review, weak test boundaries, awkward security hardening, and high risk when changing small UI behaviours.

---

## Considered Options

### Option 1: Keep the monolithic generated index.html

Continue maintaining the UI as a single generated HTML file containing all logic, markup, styles, and assets.

**Pros:**
- Zero build tooling
- Trivially portable — one file is the whole application

**Cons:**
- Code review of any change means reviewing one very large file
- No module boundaries, so no meaningful unit test surface
- Security-sensitive logic (escaping, URL validation) is interleaved with everything else
- Small behaviour changes carry high regression risk

### Option 2: Adopt a full framework toolchain

Rebuild the UI as a conventional framework application (e.g. Vite + a component framework) with dependency-based builds and component tests.

**Pros:**
- Strong component and test conventions
- Component rendering with stronger default escaping

**Cons:**
- Introduces a dependency tree and toolchain to install, audit, and keep patched
- Disproportionate to the current UI scope, which is small and framework-free

### Option 3: Source-first static modules without third-party dependencies *(chosen)*

Split the UI into small source modules with a dependency-free build script that produces the static `dist/` output.

**Pros:**
- Reviewable, testable module boundaries without taking on a dependency tree
- Security-sensitive logic gets explicit module boundaries
- Builds and tests run with no dependency installation

**Cons:**
- Hand-rolled build and renderer carry maintenance responsibility that a framework would otherwise absorb
- Will need revisiting if the UI grows materially

---

## Decision

Use a source-first static frontend layout:

- `index.html` is a small entry point.
- `src/` contains separate modules for configuration, API access, state, rendering, Markdown handling, storage, and security helpers.
- `public/` contains static visual assets.
- `scripts/build.mjs` produces `dist/` without requiring third-party dependencies.
- Tests cover source structure, pure helper behaviour, and build output.

The UI remains framework-free for now because the current scope is small and no dependency installation is required to build or test it. If the UI grows materially, a conventional Vite application with component tests should be reconsidered.

---

## Justification

The monolithic artifact was blocking the things a public-facing UI needs most: reviewable changes, testable boundaries, and isolatable security-sensitive logic. Source modules solve those problems directly. A full framework toolchain would also solve them, but at the cost of a dependency tree that is disproportionate to the current scope; the framework-free approach keeps the build and test path dependency-free while leaving a clear upgrade route if the UI grows.

---

## Enforcement

- Tests assert the source structure, pure helper behaviour, and build output described in the Decision
- `scripts/build.mjs` is the only build path to `dist/`; it must not acquire third-party dependencies without revisiting this ADR
- All state and API response values must be escaped before insertion into `innerHTML`; security helpers live in their own modules
- Material growth in UI scope should trigger the framework reconsideration described in the Decision, superseding this ADR

---

## Consequences

Positive:
- The application is easier to review and evolve on the way to public release
- Security-sensitive logic such as URL validation, output escaping, and Markdown rendering now has explicit module boundaries

Negative / trade-offs:
- The renderer is still a lightweight template-string implementation. It must continue escaping all state and API response values before insertion into `innerHTML`; richer interaction or larger UI surfaces should trigger a move to component rendering with stronger default escaping

---

## Related

- [ADR-009: Ship mnemo-ui as a standalone static container](009-standalone-ui-container.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
