# ADR-011: Tiered review model for KB contributions

> **Status:** `Accepted`
> **Date:** 2026-06-30
> **Review date:** 2027-06-30

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-011 |
| **Title** | Tiered review model for KB contributions |
| **Status** | Accepted |
| **Date** | 2026-07-06 |
| **Review date** | 2027-06-30 |
| **Supersedes** | [ADR-005: AI must not contribute to the knowledge base without human review](005-human-review-governance.md) |
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

ADR-005 established that AI must not contribute to the knowledge base without human review, and that every pipeline submission must result in a pull request approved by a human before merge. That position was the right starting point: it established a clear, auditable governance floor and shaped the project's identity as a human-in-the-loop system.

This ADR supersedes ADR-005. The blanket human review requirement it established is no longer the correct position as the system matures toward agentic operation.

As Mnemosyne evolves to include self-curation capabilities, lessons-learnt capture, and agent-loop contributions, the volume and variety of proposed KB contributions will increase significantly. Uniform human review at that scale creates a bottleneck that incentivises rubber-stamping — a human approval in name only, which is worse than a well-designed automated gate because it creates the appearance of oversight without its substance.

At the same time, not all KB contributions carry the same risk. A routine reference document update and a change to the pipeline's governance policy are not equivalent, and treating them identically is an inappropriate conflation. Documents that define how the system governs itself require unconditional human authority; documents that describe what the system knows do not.

Additionally, as the system operates across more scenarios and edge cases, agents will encounter situations that no human explicitly designed for. A purely reactive governance model — where humans only ratify what they already understand — cannot capture governance gaps that arise from novel agent behaviour. The system needs a path for agents to surface and propose governance improvements, while ensuring humans retain final authority over anything that affects the change process itself.

This ADR replaces the uniform human review requirement with a tiered model: dual adversarial model review as a universal gate, with the exit condition varying by content tier.

---

## Considered Options

### Option 1: Uniform human review for all contributions (ADR-005 model)

Continue requiring human PR approval for every KB contribution regardless of content type.

**Pros:**
- Simplest governance posture; no classification of contributions required
- Every piece of KB content has a human-approval audit trail

**Cons:**
- Does not scale as contribution volume increases with agentic operation
- Creates a bottleneck that incentivises rubber-stamping at high volume, which is worse than a well-designed automated gate
- Treats a routine reference document update identically to a change in governance policy — an inappropriate equivalence

### Option 2: Fully automated review with human override

Allow automated review to approve and merge contributions, with humans able to override.

**Pros:**
- Maximum throughput; no human bottleneck

**Cons:**
- Inverts the governance model established in ADR-005
- Humans reviewing after the fact have far less influence than humans approving before merge
- Incompatible with the project's identity and regulated-environment positioning

### Option 3: Tiered review model with dual adversarial gate *(chosen)*

Classify KB contributions by content tier. Apply dual adversarial model review as a universal gate. The exit condition after that gate differs by tier: standard content can be approved on model agreement; governance and constitutional content requires human sign-off informed by the models' recommendation.

**Pros:**
- Scales for high-volume standard contributions without sacrificing oversight
- Preserves mandatory human authority over the documents that govern the change process itself
- Dual adversarial review provides stronger automated quality assurance than a single model reviewer
- Model disagreement is a reliable uncertainty signal for escalation
- Reviewer model slots are pluggable — consistent with ADR-004
- Humans reviewing governance content are aided by adversarial analysis, making their review more rigorous rather than a cold read

**Cons:**
- More complex than uniform review; requires accurate tier classification of contributions
- Tier classification is itself a governance document and must be treated as such (see Enforcement)
- Dual adversarial review adds latency relative to single-model review

---

## Decision

KB contributions are classified into two tiers. Dual adversarial model review is the universal mechanism applied to both tiers. The exit condition after review differs by tier.

**Tier 1 — Standard content**

Factual KB content: how-to documents, tutorials, reference material, explanations, terminology, cross-references, and lessons-learnt entries captured from agent operation.

- Dual adversarial model review is applied
- If both reviewer models agree to accept: the PR may be approved and merged without human sign-off
- If the reviewer models disagree: the contribution is automatically escalated to human review
- Human review remains available at any time; this tier sets the *minimum* gate, not a ceiling

**Tier 2 — Governance and constitutional content**

Any document that defines, modifies, or affects the change process itself: ADRs, pipeline configuration, review policy, trust tier definitions, enforcement rules, and any document that determines what belongs in Tier 2.

- Dual adversarial model review is applied, producing a structured recommendation (accept / reject / concerns)
- Human review is mandatory regardless of model agreement; the models' recommendation is input to the human reviewer, not a substitute for their judgement
- This requirement is unconditional and is not configurable

**Escalation**

Model disagreement on any contribution, regardless of tier, triggers mandatory escalation to human review. A disagreement between adversarial reviewers is treated as an uncertainty signal, not a tie-break to be resolved automatically.

**Governance gap identification**

As Mnemosyne operates agentically, it may encounter scenarios not covered by existing governance. Agents may surface these as GitHub issues flagging a governance gap. Initially, a human determines whether to draft the corresponding ADR or to ask the agent to propose a draft. As trust in the pipeline matures, agents may propose governance documents directly; such proposals are always Tier 2 and follow the mandatory human review path.

---

## Justification

ADR-005's position was correct for the system at the time it was written. Blanket human review established trust, created a clear audit trail, and was the right constraint while the pipeline was being proven. This ADR does not repudiate that — it evolves from it.

The tiered model replaces the letter of ADR-005 while preserving its intent: human accountability for KB content. The mechanism changes; the principle does not. Where ADR-005 expressed that principle as "a human approves everything," this ADR expresses it as "a human approves anything that governs how the system works, and automated adversarial review handles the rest with human escalation on uncertainty."

Dual adversarial review with cross-family model pairing provides genuine independent verification: different training data, different RLHF approaches, and deliberately opposed review prompts (one arguing for acceptance, one hunting for rejection) make it substantially harder for subtly incorrect content to pass both gates than to pass a single reviewer. Model disagreement as an escalation signal is the most valuable output of the adversarial pairing — it surfaces genuine uncertainty reliably.

The constitutional protection for Tier 2 content is not merely a quality gate — it is an architectural safeguard. Documents that define how the system governs itself are different in kind from documents that describe what the system knows. Allowing automated review to be the final authority over governance documents would permit the review model itself to erode the governance constraints it operates under. This must not be possible, and the constraint must be self-referential: the document that defines Tier 2 membership is itself a Tier 2 document.

The governance gap identification path acknowledges a fundamental epistemic limitation: humans cannot govern scenarios they are unaware of. An agent operating at scale will encounter novel situations before any human does. Capturing those observations and surfacing them as proposed governance changes — subject to mandatory human ratification — extends the governance model's reach without surrendering human authority over its content.

---

## Enforcement

- The tier of a contribution must be determined at PR creation time and recorded in the PR metadata
- The document defining tier membership (this ADR) is itself Tier 2; changes to tier definitions require human review
- Dual adversarial review must use models from different families; same-family pairing must be rejected at configuration time
- The adversarial prompts must be structured asymmetrically: one reviewer is instructed to argue for acceptance, one to hunt for rejection
- Model agreement and disagreement outcomes must be recorded in PR review comments for audit purposes
- Auto-approval on model agreement (Tier 1) must not be possible if either reviewer model is unavailable; unavailability triggers escalation to human review
- Reviewer model slots are configured via the pluggable LLM layer (ADR-004); specific model identities are operational decisions, not architectural ones
- The pipeline service account must not have merge permissions for Tier 2 PRs under any circumstances

---

## Consequences

Positive:
- Standard KB contributions scale without creating a rubber-stamp bottleneck
- Governance and constitutional documents retain unconditional human oversight
- Model disagreement provides a reliable, auditable uncertainty signal
- Agentic governance gap identification extends the system's self-awareness without surrendering human authority
- Reviewer pluggability is consistent with the existing LLM abstraction layer

Negative / trade-offs:
- Tier classification of contributions adds complexity to the ingestion pipeline
- Dual adversarial review adds latency relative to single-model review
- Cross-family model pairing requires access to models from at least two distinct provider families
- Tier 2 mandatory human review remains a bottleneck for governance changes; governance evolution is intentionally slow

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-005: AI must not contribute to the knowledge base without human review](005-human-review-governance.md) *(will be superseded when this ADR is accepted)*
- [ADR-006: MCP as intake interface only](006-mcp-intake-only.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
