# ADR-003: Use Diataxis as the content classification taxonomy

> **Status:** `Accepted`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-003 |
| **Title** | Use Diataxis as the content classification taxonomy |
| **Status** | Accepted |
| **Date** | 2026-06-08 |
| **Review date** | 2027-06-08 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Tags** | `content` `classification` `AI` `diataxis` |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

The ingestion pipeline must classify every document before it is processed and committed to the knowledge base. A consistent classification scheme is required to ensure documents are structured appropriately, routed to the correct KB section, and augmented with accurate metadata.

A taxonomy was needed that is well-defined enough for an LLM to apply consistently, meaningful enough to improve KB navigability, and widely enough understood that contributors and reviewers can reason about classifications without specialist knowledge.

---

## Considered Options

### Option 1: Custom taxonomy

Define a project-specific classification scheme tailored to Mnemosyne's use cases.

**Pros:**
- Can be precisely fitted to the project's content types

**Cons:**
- Requires definition and maintenance
- No external documentation or community familiarity
- LLM classification would require more extensive prompt engineering

### Option 2: No classification

Store documents without classification and rely on search and tagging.

**Pros:**
- No classification step in the pipeline; simpler

**Cons:**
- Reduces KB navigability significantly
- Loses a core value proposition of the ingestion engine

### Option 3: Diataxis *(chosen)*

Use the Diataxis documentation framework, which defines four content types: **tutorial** (learning-oriented), **how-to** (task-oriented), **reference** (information-oriented), and **explanation** (understanding-oriented).

**Pros:**
- Well-defined, publicly documented framework with extensive guidance
- Widely adopted in the technical documentation community
- LLMs classify Diataxis types reliably with appropriate prompting
- Four clear categories are sufficient for most KB content without being overly complex
- Organisational sub-labels can be applied beneath each type for further granularity

**Cons:**
- Not every document fits neatly into one of four types — edge cases require explicit handling
- Requirements and architecture documents can be misclassified; must be explicitly directed to **explanation** in the system prompt

---

## Decision

Mnemosyne will use the Diataxis framework as its primary content classification taxonomy, with four types: tutorial, how-to, reference, and explanation.

---

## Justification

Diataxis provides a principled, well-documented taxonomy that LLMs can apply consistently. It is sufficiently expressive for knowledge base content without introducing excessive complexity. The four-type structure maps well to the range of documents typically submitted to a technical or organisational KB. Known edge cases (requirements and architecture documents) are handled by explicit system prompt guidance directing them to the **explanation** type.

---

## Enforcement

- The LLM system prompt must explicitly instruct the classifier to route requirements and architecture documents to **explanation**, not reference or how-to
- Classification outcomes are logged as pipeline metrics; sustained misclassification rates should trigger a prompt review
- Human reviewers should reject PRs where classification is clearly incorrect

---

## Consequences

Positive:
- Consistent, navigable KB structure from day one
- Classification step adds genuine value to submitted documents
- External contributors can understand the taxonomy without project-specific documentation

Negative / trade-offs:
- Edge cases require ongoing prompt maintenance
- Some documents may not map cleanly to any Diataxis type and will require manual override

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-005: AI must not contribute without human review](005-human-review-governance.md)
- [Diataxis framework documentation](https://diataxis.fr)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
