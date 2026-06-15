# ADR-008: Expose MCP as a network endpoint and allow thin client transport bridges

> **Status:** `Accepted`
> **Date:** 2026-06-15
> **Review date:** 2027-06-15

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-008 |
| **Title** | Expose MCP as a network endpoint and allow thin client transport bridges |
| **Status** | Accepted |
| **Date** | 2026-06-15 |
| **Review date** | 2027-06-15 |
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

Mnemosyne exposes MCP so AI agents such as Cursor, Claude, Copilot, ChatGPT, and other MCP-compatible clients can submit documents to the ingestion engine.

MCP clients do not all support the same transport modes. Some clients can connect directly to network MCP servers over SSE or HTTP-style transports. Others only support launching local stdio MCP servers via a `command` and `args` configuration.

A decision was needed on where the authoritative MCP server should live, and whether local wrappers should contain Mnemosyne-specific ingestion logic.

---

## Considered Options

### Option 1: Put MCP logic in per-client wrappers

Create a different local MCP server or plugin wrapper for each client family.

**Pros:**
- Works with clients that only support local stdio MCP servers
- Can adapt to client-specific quirks

**Cons:**
- Duplicates ingestion behavior outside `mnemo-core`
- Risks diverging behavior between clients
- Makes governance harder to reason about
- Requires multiple implementations of the same tools

### Option 2: Make `mnemo-core` the authoritative network MCP server, with optional thin wrappers *(chosen)*

Expose the MCP server from `mnemo-core` as a network endpoint. Clients that support remote/SSE MCP connect directly. Clients that only support stdio may use a thin transport bridge that forwards protocol traffic to `mnemo-core`.

**Pros:**
- Keeps ingestion, classification, publishing, authentication, and governance in one service
- Lets compatible agents connect directly without a wrapper
- Allows compatibility bridges for clients that require stdio
- Avoids duplicating tool behavior and policy in client-specific adapters

**Cons:**
- Some clients still require a local bridge process
- Operators must understand which transport their MCP client supports
- Mnemosyne must keep its network MCP endpoint stable and well documented

---

## Decision

`mnemo-core` is the authoritative MCP server for Mnemosyne. It exposes MCP over a network endpoint using SSE at `/mcp/sse`, with client messages posted to `/mcp/messages`.

MCP clients that support remote or SSE MCP servers should connect to `mnemo-core` directly. Clients that only support local stdio MCP servers may use a thin bridge process, but that bridge is only a transport adapter. It must not contain ingestion, publishing, classification, authentication, or governance logic.

---

## Justification

The ingestion engine is the boundary where Mnemosyne enforces authentication, preview versus ingest behavior, LLM provider selection, publishing, and human-review governance. Keeping the MCP tools in `mnemo-core` ensures REST and MCP intake share the same pipeline and policy.

Client-specific wrappers are useful for transport compatibility, but making them authoritative would duplicate business rules and increase the risk that some clients bypass review or behave differently from others.

---

## Enforcement

- MCP tool definitions and ingestion behavior live in `mnemo-core`
- Transport bridges must forward to the `mnemo-core` MCP endpoint and must not reimplement ingestion tools
- The mounted MCP routes must be covered by tests so `/mcp/sse` and `/mcp/messages` do not regress
- Documentation must distinguish direct network MCP configuration from stdio bridge configuration

---

## Consequences

Positive:
- Compatible agents can talk directly to the ingestion engine
- All clients share the same ingestion behavior and governance boundary
- Stdio-only clients remain supportable through lightweight bridges

Negative / trade-offs:
- Some MCP clients require additional local bridge configuration
- The MCP transport surface becomes part of the supported `mnemo-core` API

---

## Related

- [ADR-006: MCP server is an intake interface only, not a retrieval interface](006-mcp-intake-only.md)
- [ADR-005: AI must not contribute without human review](005-human-review-governance.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
