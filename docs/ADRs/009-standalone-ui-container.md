# ADR-009: Ship mnemo-ui as a standalone static container

> **Status:** `Accepted`
> **Date:** 2026-06-16
> **Review date:** 2027-06-16

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-009 |
| **Title** | Ship mnemo-ui as a standalone static container |
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

`mnemo-ui` is an optional browser frontend for `mnemo-core`. It talks to `mnemo-core` over HTTP and does not require server-side rendering or a JavaScript application server at runtime.

The first containerization pass served a self-contained generated `index.html`. That was acceptable as a bootstrap artifact, but not as the long-term source architecture for a public-facing UI. ADR-010 supersedes the monolithic-source assumption and keeps this ADR focused on runtime packaging.

---

## Considered Options

### Option 1: Serve the UI from mnemo-core

Bundle the built UI assets into the `mnemo-core` image and serve them from the existing API process.

**Pros:**
- One container to deploy
- No CORS or cross-origin configuration between UI and API

**Cons:**
- Couples UI and core release cycles, undermining the separate-artefact model of ADR-001
- Headless deployments carry UI assets they do not use
- The API process takes on static-file-serving concerns it does not need

### Option 2: JavaScript application server container

Ship the UI with a Node.js server process (SSR or a serving framework) in its own container.

**Pros:**
- Room for server-side rendering if ever needed
- Familiar packaging for JavaScript frontends

**Cons:**
- The UI has no server-side rendering requirement — the process adds attack surface and patch burden with no benefit
- Larger image, more runtime dependencies to track for CVEs

### Option 3: Static-only unprivileged Nginx container *(chosen)*

Build the UI to a static `dist/` directory and serve it from an unprivileged Nginx container, with no JavaScript runtime in the image.

**Pros:**
- Minimal runtime attack surface — static files and a hardened, widely-audited server
- Independent deployment and release cadence from `mnemo-core`
- Security headers can be enforced at the serving layer

**Cons:**
- Requires the UI to remain fully static; any future SSR need would force repackaging
- Cross-origin configuration between UI and API must be handled explicitly

---

## Decision

Build `mnemo-ui` into a static `dist/` directory and serve that directory from an unprivileged Nginx container listening on port `8080`. Keep the runtime image static-only and avoid adding a JavaScript server process.

Add defense-in-depth headers at the Nginx layer:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `X-Frame-Options: DENY`
- `Permissions-Policy` disabling browser capabilities that the UI does not use
- CSP blocking object embedding, forms, base URI changes, and framing

---

## Justification

The UI is static by nature, so the packaging should not introduce a server runtime the application does not need. A static-only unprivileged Nginx container gives the smallest practical attack surface for a public-facing UI, keeps `mnemo-ui` independently deployable in line with the separate-artefact model of ADR-001, and provides a natural enforcement point for security headers. The trade-offs (explicit CORS handling, no SSR path without repackaging) are acceptable because the UI is optional, framework-free, and small in scope.

---

## Enforcement

- The `mnemo-ui` Dockerfile builds from `dist/` onto an unprivileged Nginx base image; no JavaScript runtime is present in the final image
- The security headers listed in the Decision are maintained in the Nginx configuration and shipped with the image
- Any proposal to add a server-side process to the UI runtime should reference and supersede this ADR

---

## Consequences

Positive:
- The container has a small runtime attack surface
- `mnemo-ui` can be deployed independently from `mnemo-core`

Negative / trade-offs:
- The current source uses JavaScript modules and CSS served as static files. The CSP still allows inline script/style compatibility while the UI remains framework-free and static, but future bundling with hashed external assets should tighten this further

---

## Related

- [ADR-001: Monorepo with separate build artefacts](001-monorepo-structure.md)
- [ADR-010: Maintain mnemo-ui as source modules](010-source-first-ui.md)
- [ADR-012: Container-level decomposition of Mnemosyne](012-container-decomposition.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
