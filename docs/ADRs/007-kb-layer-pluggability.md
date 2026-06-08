# ADR-007: Implement a pluggable KB layer with MkDocs Material as the reference implementation

> **Status:** `Accepted`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-007 |
| **Title** | Implement a pluggable KB layer with MkDocs Material as the reference implementation |
| **Status** | Accepted |
| **Date** | 2026-06-08 |
| **Review date** | 2027-06-08 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Tags** | `KB` `architecture` `pluggability` `mkdocs` |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

Mnemosyne processes documents and commits them to a Git repository. A knowledge base layer sits on top of that repository, serving its content to users. Different organisations have different KB tools, preferences, and constraints — some will want a lightweight static site, others may require integration with existing enterprise platforms such as SharePoint.

A decision was needed on whether to mandate a specific KB tool or to treat the KB layer as pluggable.

---

## Considered Options

### Option 1: Mandate a single KB tool

Require all deployments to use a specific KB platform, such as MkDocs Material.

**Pros:**
- Simpler to document and support
- Consistent user experience across deployments

**Cons:**
- Excludes organisations with existing KB investments they cannot or will not replace
- Particularly problematic for enterprise adopters already using SharePoint or similar platforms
- Contradicts the open source goal of broad compatibility

### Option 2: Pluggable KB layer with a reference implementation *(chosen)*

Treat the KB layer as a pluggable component. Define the contract the KB layer must satisfy (ability to serve markdown files from a Git repository) and provide MkDocs Material as the reference implementation. Document alternative options.

**Pros:**
- Broad compatibility — organisations can use their existing KB platform
- Reference implementation provides a high-quality, well-documented starting point
- Low barrier to enterprise adoption, particularly for Microsoft 365 environments
- Consistent with the pluggable LLM layer approach (ADR-004)

**Cons:**
- Mnemosyne cannot guarantee a consistent user experience across all KB providers
- Some providers (notably SharePoint) have constraints that limit markdown rendering quality
- Documentation and support burden increases with the number of supported options

---

## Decision

The KB layer will be treated as pluggable. Any tool capable of serving markdown files from a Git repository is a valid KB provider. MkDocs Material will be the reference implementation, fully documented and supported. Additional providers are documented with their respective constraints.

---

## Justification

The core value of Mnemosyne lies in the ingestion pipeline, not in the KB layer. Mandating a specific KB tool would unnecessarily restrict adoption, particularly in enterprise environments with existing platform investments. The pluggable approach maximises compatibility while the reference implementation ensures there is always a well-supported, high-quality option for users without existing KB tooling.

SharePoint is explicitly acknowledged as a supported option despite its constraints on markdown rendering and Git integration, because it represents a significant pragmatic choice for many enterprise organisations already operating within the Microsoft 365 ecosystem.

---

## Enforcement

- The pipeline must commit output as standard markdown files compatible with any conforming KB provider
- Pipeline output must not rely on KB-provider-specific features or formatting
- Documentation for each supported KB provider must clearly note any constraints or limitations
- KB provider configuration must be handled via environment variables or deployment configuration, not hardcoded

---

## Consequences

Positive:
- Broad compatibility with existing KB platforms
- Low barrier to enterprise adoption
- Reference implementation provides a clear, well-supported default

Negative / trade-offs:
- User experience varies across KB providers
- SharePoint integration involves constraints on markdown rendering and Git workflow that cannot be resolved by Mnemosyne
- Support burden increases with the number of documented providers

---

## Supported KB Providers

| Provider | Status | Notes |
|----------|--------|-------|
| MkDocs Material | ⭐ Reference | Fully supported and documented |
| Docusaurus | Supported | React-based; well-suited to developer-focused KBs |
| VitePress | Supported | Vue-based; fast and lightweight |
| Obsidian | Supported | Popular for individual and team knowledge management |
| Plain GitHub | Supported | Zero setup; markdown renders natively |
| SharePoint | Supported (enterprise) | Pragmatic choice for Microsoft 365 organisations; markdown rendering and Git integration have constraints |

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-006: MCP as intake interface only](006-mcp-intake-only.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
