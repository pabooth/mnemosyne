# ADR-001: Use a monorepo with separate build artefacts

> **Status:** `Accepted`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-001 |
| **Title** | Use a monorepo with separate build artefacts |
| **Status** | Accepted |
| **Date** | 2026-06-08 |
| **Review date** | 2027-06-08 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Tags** | `repository` `structure` `build` |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

Mnemosyne consists of two distinct deployable components: `mnemo-core` (the ingestion engine, REST API, and MCP server) and `mnemo-ui` (the optional web frontend). These components have different deployment profiles — `mnemo-core` can be run headlessly without `mnemo-ui` — and may evolve at different cadences over time.

A decision was needed on whether to maintain these as a single repository or as separate repositories, and how to handle distribution artefacts in either case.

---

## Considered Options

### Option 1: Single repository, single artefact

Keep all code in one repository and ship a single combined release artefact.

**Pros:**
- Simplest possible setup
- No coordination overhead between repos

**Cons:**
- Forces users who want only `mnemo-core` to take the full codebase
- Does not reflect the architectural separation between core and UI

### Option 2: Separate repositories

Maintain `mnemo-core` and `mnemo-ui` as independent repositories with independent release pipelines.

**Pros:**
- Clean separation; users clone only what they need
- Independent versioning and release cadences

**Cons:**
- Significant overhead for a project with one primary maintainer
- Cross-component changes require coordinated PRs across two repos
- Harder for contributors to get started
- Premature for the current stage of the project

### Option 3: Monorepo with separate build artefacts *(chosen)*

Maintain all code in a single repository under `/mnemo-core` and `/mnemo-ui` directories, but produce separate versioned build artefacts from the CI/CD pipeline.

**Pros:**
- Development simplicity — one repo, one issue tracker, one CI pipeline
- Cross-component changes are a single PR
- Folder structure signals architectural intent without the overhead of two repos
- Users can still pull only the component they need via separate Docker images or release archives
- Can be split into separate repos later if the project grows to warrant it

**Cons:**
- Slightly more complex CI/CD pipeline to produce multiple artefacts
- Version numbers are shared across components unless explicitly decoupled

---

## Decision

We will maintain Mnemosyne as a monorepo with `mnemo-core` and `mnemo-ui` as top-level directories, and produce separate versioned build artefacts for each component from the CI/CD pipeline.

---

## Justification

At the current stage of the project, the overhead of maintaining two repositories outweighs the benefits. The monorepo structure makes development and contribution straightforward while the folder-level separation preserves the architectural boundary between core and UI. Separate artefacts ensure users are not forced to take the full codebase if they only need headless deployment. The decision can be revisited if the project reaches a scale where independent release cadences or separate maintainership of the UI becomes necessary.

---

## Enforcement

- Repository structure is maintained by convention and documented here
- CI/CD pipeline configuration enforces separate artefact production per component
- Any proposal to restructure the repository should reference and supersede this ADR

---

## Consequences

Positive:
- Low friction for contributors — single clone, single CI pipeline
- Headless deployments are well-supported via separate `mnemo-core` artefacts
- Architectural separation is visible and documented without operational overhead

Negative / trade-offs:
- Shared version numbers across components unless explicitly managed
- If the project grows significantly, migration to separate repos will be required

---

## Related

- [ADR-005: AI must not contribute without human review](005-human-review-governance.md)
- [ADR-006: MCP as intake interface only](006-mcp-intake-only.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
