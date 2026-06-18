# ADR-009: Ship mnemo-ui as a standalone static container

> **Status:** `Accepted`
> **Date:** 2026-06-16
> **Review date:** 2027-06-16

---

## Context

`mnemo-ui` is an optional browser frontend for `mnemo-core`. It talks to `mnemo-core` over HTTP and does not require server-side rendering or a JavaScript application server at runtime.

The first containerization pass served a self-contained generated `index.html`. That was acceptable as a bootstrap artifact, but not as the long-term source architecture for a public-facing UI. ADR-010 supersedes the monolithic-source assumption and keeps this ADR focused on runtime packaging.

## Decision

Build `mnemo-ui` into a static `dist/` directory and serve that directory from an unprivileged Nginx container listening on port `8080`. Keep the runtime image static-only and avoid adding a JavaScript server process.

Add defense-in-depth headers at the Nginx layer:

- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `X-Frame-Options: DENY`
- `Permissions-Policy` disabling browser capabilities that the UI does not use
- CSP blocking object embedding, forms, base URI changes, and framing

## Consequences

The container has a small runtime attack surface and can be deployed independently from `mnemo-core`.

The current source uses JavaScript modules and CSS served as static files. The CSP still allows inline script/style compatibility while the UI remains framework-free and static, but future bundling with hashed external assets should tighten this further.
