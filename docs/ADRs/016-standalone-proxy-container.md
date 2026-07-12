# ADR-016: Extract edge routing into mnemo-proxy

> **Status:** `Accepted`
> **Date:** 2026-07-11
> **Review date:** 2027-07-11

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-016 |
| **Title** | Extract edge routing into mnemo-proxy |
| **Status** | Accepted |
| **Date** | 2026-07-11 |
| **Review date** | 2027-07-11 |
| **Supersedes** | ADR-012 (proxy ownership only) |
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

The reference reverse proxy was stored under `deploy/` and injected into a
third-party nginx image at runtime. Although Compose ran it separately, the
proxy was not a Mnemosyne component: it had no component directory, image,
release artifact, CI build, or explicit ownership boundary. That made edge
routing appear to be deployment plumbing attached to `mnemo-core` instead of
an independently built runtime concern.

ADR-012 defines deployed-service ownership, while ADR-009 establishes that the
UI and core have independent runtime boundaries. The entry point routing both
services needs the same explicit treatment.

## Considered Options

### Option 1: Keep a mounted deployment configuration

Continue mounting `deploy/reverse-proxy/nginx.conf` into an upstream nginx
image.

**Pros:**
- No additional first-party image
- Operators can edit the mounted file directly

**Cons:**
- No versioned proxy artifact or CI image build
- Routing ownership remains implicit
- Packaged and source deployments assemble the runtime differently

### Option 2: Build a standalone mnemo-proxy component *(chosen)*

Create a top-level component containing the proxy image and routing
configuration, and publish it alongside the other container images.

**Pros:**
- Gives routing an explicit release and failure boundary
- Makes source and packaged Compose deployments consume the same artifact
- Keeps edge behavior out of `mnemo-core` while preserving one public origin

**Cons:**
- Adds another image to build, publish, and update
- The reference configuration assumes Compose service names for its upstreams

## Decision

`mnemo-proxy` is an optional, standalone deployable owned by Mnemosyne. It
routes `/` to `mnemo-ui` and `/api/`, `/mcp/`, and `/health` to `mnemo-core`.
It contains no business, authentication, ingestion, publishing, or governance
logic. `mnemo-core` remains independently deployable for headless use.

Source Compose builds `mnemo-proxy` from its top-level directory. Packaged
Compose pulls the versioned `ghcr.io/pabooth/mnemo-proxy` image. Operators may
still put a site-specific TLS ingress in front of it. Both `mnemo-proxy` and
`mnemo-ui` are enabled through the optional Compose `ui` profile; an
unprofiled Compose startup runs only `mnemo-core`.

## Justification

Edge routing is a runtime responsibility with its own security, availability,
and release concerns. A first-party image makes that boundary reviewable and
reproducible without coupling it to the application process. Keeping the
component optional preserves headless and alternative-ingress deployments.

## Enforcement

- Proxy configuration and its Dockerfile live under `mnemo-proxy/`.
- CI builds the proxy image and validates the complete Compose model.
- Compose assigns the proxy and UI to the optional `ui` profile.
- Releases publish a versioned proxy image and standalone archive.
- Application or governance logic must not be added to `mnemo-proxy`.
- Changes that move edge routing into another component must supersede this ADR.

## Consequences

Positive:
- `mnemo-core` owns only API, MCP, pipeline, job, and publishing concerns.
- Proxy behavior is versioned and tested as a distinct artifact.
- Packaged deployments no longer depend on a host-mounted nginx config.

Negative / trade-offs:
- Releases contain and publish one additional artifact.
- Custom upstream names require a custom image or configuration override.

## Related

- [ADR-009: Standalone UI container](009-standalone-ui-container.md)
- [ADR-012: Container-level decomposition](012-container-decomposition.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
