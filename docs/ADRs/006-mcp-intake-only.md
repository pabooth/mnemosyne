# ADR-006: MCP server is an intake interface only, not a retrieval interface

> **Status:** `Accepted`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-006 |
| **Title** | MCP server is an intake interface only, not a retrieval interface |
| **Status** | Accepted |
| **Date** | 2026-06-08 |
| **Review date** | 2027-06-08 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Tags** | `MCP` `architecture` `AI` `interfaces` |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

Mnemosyne exposes an MCP (Model Context Protocol) server to allow AI agents — such as Claude, ChatGPT, or other MCP-compatible clients — to interact with the system. A decision was needed on the scope of that interface: should it be limited to document submission (intake), or should it also support KB querying and retrieval?

Mnemosyne is an ingestion engine. The knowledge base itself is a separate system (e.g. MkDocs Material, Docusaurus, or another KB provider). This architectural boundary is relevant to the MCP scope decision.

---

## Considered Options

### Option 1: MCP server supports both intake and KB retrieval

Expose MCP tools for both submitting documents to the pipeline and querying the KB.

**Pros:**
- A single MCP connection gives AI agents full read/write access to the KB ecosystem
- Convenient for AI agent workflows that need to both query and contribute

**Cons:**
- Mnemosyne is not the KB — querying the KB through Mnemosyne conflates two distinct systems
- Retrieval capability would require Mnemosyne to maintain a connection to the KB layer, increasing coupling
- Increases the attack surface and complexity of the MCP server
- Retrieval is better handled by connecting an AI agent directly to the KB provider

### Option 2: MCP server supports intake only *(chosen)*

The MCP server exposes tools for document submission to the ingestion pipeline only. KB querying and retrieval are out of scope.

**Pros:**
- Maintains a clean architectural boundary between the ingestion engine and the KB
- Keeps the MCP server simple and focused
- Retrieval is delegated to the KB provider, which is better placed to serve it
- Reduces coupling between mnemo-core and the KB layer
- Consistent with the principle that Mnemosyne is an ingestion engine, not a KB

**Cons:**
- AI agents that want both intake and retrieval must connect to two separate systems
- Slightly less convenient for agent workflows that need both capabilities

---

## Decision

The Mnemosyne MCP server will expose intake tools only. It will not provide KB querying or retrieval capabilities. AI agents requiring KB retrieval should connect directly to the KB provider.

---

## Justification

Mnemosyne's purpose is document ingestion and processing. The knowledge base is a separate system with its own interface. Combining intake and retrieval in the Mnemosyne MCP server would blur this boundary, increase coupling, and add complexity that is not warranted by the use cases. AI agents that need retrieval have better options — connecting directly to the KB provider, which is purpose-built for serving content. The intake-only constraint keeps the MCP server focused, maintainable, and consistent with the system's overall architecture.

---

## Enforcement

- The MCP server must not implement any tool that reads from or queries the KB
- Code review should reject any PR that adds retrieval tools to the MCP server without a superseding ADR
- MCP server documentation must clearly state that the interface is intake-only

---

## Consequences

Positive:
- Clean architectural boundary between ingestion engine and KB
- MCP server remains simple and focused
- Reduced coupling between mnemo-core and the KB layer

Negative / trade-offs:
- AI agents needing both intake and retrieval must manage two connections
- Some users may find this limitation surprising and expect a unified interface

---

## Related

- [ADR-005: AI must not contribute without human review](005-human-review-governance.md)
- [ADR-007: Pluggable KB layer](007-kb-layer-pluggability.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
