# ADR-004: Implement a pluggable LLM provider layer

> **Status:** `Accepted`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-004 |
| **Title** | Implement a pluggable LLM provider layer |
| **Status** | Accepted |
| **Date** | 2026-06-08 |
| **Review date** | 2027-06-08 |
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

The ingestion pipeline uses a large language model for document classification, content augmentation, and formatting. The initial implementation was built against the Anthropic API specifically. As an open source project, Mnemosyne must not require users to use a particular LLM provider — this would create a hard dependency on a paid external service and limit adoption.

Additionally, some users will have data residency, cost, or privacy requirements that make local or self-hosted LLM deployment (e.g. Ollama) preferable or mandatory.

---

## Considered Options

### Option 1: Hard-code Anthropic API

Continue with a direct dependency on the Anthropic API.

**Pros:**
- No abstraction layer required; simpler codebase
- Anthropic models are well-suited to the classification and augmentation tasks

**Cons:**
- Forces all users to obtain and fund an Anthropic API key
- Excludes users with data residency requirements or air-gapped environments
- Creates vendor lock-in incompatible with open source principles

### Option 2: Pluggable LLM layer via environment configuration *(chosen)*

Abstract the LLM interaction behind a provider interface. The active provider and its configuration are set via environment variables. The Anthropic API is the reference implementation.

**Pros:**
- Users can choose their preferred provider without modifying code
- Supports local/self-hosted LLMs (e.g. Ollama) for fully offline deployments
- Compatible with OpenAI, Azure OpenAI, Google Gemini, and other providers
- Anthropic remains the reference and default; existing behaviour is unchanged for users who want it

**Cons:**
- Requires an abstraction layer that must be maintained as provider APIs evolve
- Classification and augmentation quality may vary across providers
- Testing across multiple providers increases CI complexity

### Option 3: Support only open/self-hosted LLMs

Remove the Anthropic dependency entirely and support only open models via Ollama or similar.

**Pros:**
- No external API dependencies; fully self-contained

**Cons:**
- Open model quality for classification and augmentation tasks is currently lower than hosted APIs
- Excludes users who prefer hosted APIs
- Contradicts the goal of broad compatibility

---

## Decision

The LLM interaction layer will be abstracted behind a configurable provider interface. The Anthropic API will be the reference implementation. Provider selection and configuration will be managed via environment variables.

---

## Justification

An open source project must not impose a paid external service dependency on its users. Abstracting the LLM layer preserves the quality of the reference implementation (Anthropic) while enabling users to substitute alternative providers based on their cost, privacy, or infrastructure requirements. The abstraction cost is justified by the significant increase in adoption potential, particularly for enterprise users with data residency requirements and self-hosters who prefer local models.

---

## Enforcement

- The LLM provider interface must be defined as an explicit abstraction in the codebase; pipeline stages must not call any provider API directly
- New provider implementations must pass a standard integration test suite
- The reference implementation (Anthropic) must remain the default and be fully documented
- Provider configuration must be handled entirely via environment variables; no provider credentials should appear in code or committed configuration

---

## Consequences

Positive:
- No vendor lock-in; broad compatibility with the LLM ecosystem
- Fully offline deployments are possible via local model providers
- Enterprise users with data residency requirements can self-host their LLM

Negative / trade-offs:
- Classification and augmentation quality may be lower with non-reference providers
- The abstraction layer adds maintenance overhead
- Provider-specific features cannot be used without breaking the abstraction

---

## Related

- [ADR-003: Use Diataxis as the content classification taxonomy](003-diataxis-classification.md)
- [ADR-005: AI must not contribute without human review](005-human-review-governance.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
