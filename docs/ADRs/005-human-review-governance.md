# ADR-005: AI must not contribute to the knowledge base without human review

> **Status:** `Superseded`
> **Date:** 2026-06-08
> **Review date:** 2027-06-08

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-005 |
| **Title** | AI must not contribute to the knowledge base without human review |
| **Status** | Superseded |
| **Date** | 2026-07-06 |
| **Review date** | - |
| **Supersedes** | — |
| **Superseded by** | ADR-011 |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

Mnemosyne uses AI at multiple stages of the ingestion pipeline — classification, augmentation, and formatting. The output of this pipeline is committed to a knowledge base that is relied upon by users. Incorrect, hallucinated, or poorly structured content reaching the KB without oversight could degrade trust in the KB and cause operational harm.

A governance position was needed on the degree of autonomy the AI pipeline is permitted to exercise over KB content.

---

## Considered Options

### Option 1: Full AI autonomy

Allow the pipeline to classify, augment, format, and merge documents directly into the KB without human review.

**Pros:**
- Fastest possible ingestion; no bottleneck on human availability
- Fully automated end-to-end workflow

**Cons:**
- AI errors, hallucinations, or misclassifications reach the KB undetected
- No audit trail of human judgement
- Erodes trust in KB content quality over time
- Incompatible with governance requirements in regulated environments

### Option 2: Human review required for merge *(chosen)*

The pipeline classifies, augments, and formats documents and commits them to a branch, raising a pull request. A human must review and approve the PR before content is merged into the KB. The pipeline has no merge permissions.

**Pros:**
- Human judgement is applied to every piece of content before it reaches the KB
- Provides a clear audit trail — every KB contribution is traceable to a human decision
- Errors and hallucinations are caught before they cause harm
- Compatible with governance requirements in regulated and enterprise environments
- Does not prevent automation of the ingestion process itself — only the final merge requires a human

**Cons:**
- Human review creates a bottleneck; high submission volumes require sufficient reviewer capacity
- Adds latency between submission and KB availability

### Option 3: AI autonomy with human override

Allow the pipeline to merge automatically, but flag low-confidence classifications for human review.

**Pros:**
- Reduces review burden for high-confidence submissions

**Cons:**
- Confidence thresholds are difficult to calibrate reliably
- Even high-confidence AI output can be incorrect
- Creates an inconsistent governance posture — some content is reviewed, some is not
- Harder to audit; unclear which content was human-reviewed

---

## Decision

The Mnemosyne pipeline must never merge content directly into the knowledge base. Every document processed by the pipeline will result in a pull request. A human must review and approve that pull request before the content is merged. This is a hard governance requirement and is not configurable.

---

## Justification

The knowledge base is a trusted information resource. Its value depends entirely on the accuracy and quality of its content. AI classification and augmentation are valuable tools for accelerating ingestion, but they are not infallible. Human review as a mandatory gate ensures that a human is always accountable for what reaches the KB, provides an audit trail for governance and compliance purposes, and prevents AI errors from compounding silently over time. The latency cost of human review is an acceptable trade-off for these guarantees.

This position is also consistent with responsible AI deployment principles: AI augments human judgement, it does not replace it.

---

## Enforcement

- The pipeline service account must have write access to feature branches only; it must not have merge permissions on the main branch
- Branch protection rules on the KB repository must require at least one human approval before merge
- This constraint must be documented prominently in the README, CONTRIBUTING.md, and deployment guides
- Any future pipeline feature that would bypass human review must be rejected at design review

---

## Consequences

Positive:
- KB content quality is maintained by human oversight
- Clear audit trail for every KB contribution
- Compatible with governance requirements in regulated environments
- Trust in the KB is preserved

Negative / trade-offs:
- Human review is a bottleneck; organisations must maintain sufficient reviewer capacity
- Latency between document submission and KB availability
- Fully automated KB ingestion is not possible by design

---

## Related

- [ADR-003: Use Diataxis as the content classification taxonomy](003-diataxis-classification.md)
- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-006: MCP as intake interface only](006-mcp-intake-only.md)
- [ADR-011: Tiered review model for KB contributions](011-tiered-review-model.md) *(proposed successor — will supersede this ADR when accepted)*

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
