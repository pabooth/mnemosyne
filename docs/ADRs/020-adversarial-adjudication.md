# ADR-020: Adjudicate an authored case against an adversarial challenge

> **Status:** `Accepted`
> **Date:** 2026-07-18
> **Review date:** 2027-07-18

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-020 |
| **Title** | Adjudicate an authored case against an adversarial challenge |
| **Status** | Accepted |
| **Date** | 2026-07-18 |
| **Review date** | 2027-07-18 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Amends** | [ADR-011: Tiered review model](011-tiered-review-model.md) |
| **Amended by** | — |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

ADR-011 introduced two cross-family reviewers with deliberately opposed prompts and treated their
agreement or disagreement as the automated gate. In operation, both models independently judged the
same document. They did not see or answer one another's reasoning, so the mechanism produced two
asymmetric inspections rather than an adversarial argument. Giving both models verdicts also mixed
partisan and adjudicative responsibilities: an acceptance advocate and rejection critic were each
asked to be both counsel and judge.

The processing model is already the author of the proposed document. Its bias toward its own work is
useful when made explicit: it should present the strongest evidence-based acceptance case, knowing
that another model will attempt to defeat it. A separate model can then adjudicate the actual dispute.

---

## Considered Options

### Option 1: Retain two independent asymmetric verdicts

Continue calibrating acceptance and rejection prompts while requiring both models to vote.

**Pros:**
- Preserves ADR-011 without changing configuration or result contracts
- Two calls can run concurrently

**Cons:**
- The reviewers still do not argue against one another
- Each model remains both partisan and decision-maker
- Disagreement reflects prompt posture as well as substantive uncertainty

### Option 2: Add a judge after two independent voting reviewers

Keep both verdicts and ask a third reviewer to resolve them.

**Pros:**
- Adds synthesis and a neutral decision point

**Cons:**
- Retains redundant reviewer verdicts
- Requires the processing model plus three review roles
- Makes the relationship between unanimity and adjudication unclear

### Option 3: Author case, adversarial challenge, and neutral adjudication *(chosen)*

Make the processing model the explicit author-advocate, have a cross-family critic rebut its case,
and have a third family adjudicate the document and both arguments.

**Pros:**
- Creates a real claim, challenge, and decision sequence
- Gives each model one coherent responsibility
- Uses three model calls in the normal path, including document processing
- Makes uncertainty explicit through a Tier 1 `escalate` decision

**Cons:**
- Review calls become sequential rather than concurrent
- Adds a judge provider and model configuration slot
- The acceptance case becomes part of the processed-document API contract

---

## Decision

The main processing model produces both the processed document and an evidence-based
`acceptance_case`. The case identifies the document's principal claims, supporting evidence,
fitness for its Diataxis purpose, anticipated objections, limitations, and expected pipeline work.
It is a bounded structured object with separate `claims`, `evidence`, `diataxis_fit`,
`anticipated_objections`, `limitations`, and `pipeline_pending` fields. It is review metadata and
is never published as KB content. Structured fields prevent the defence from becoming an
unbounded persuasive essay and give the critic distinct evidence and objection material to test.

After the PR is created, the critic receives the exact proposed document and its acceptance case. It
produces a rejection case that attempts to establish material correctness, safety, provenance,
governance, context, or document-fitness defects. It distinguishes blocking from non-blocking
concerns and treats proposed status, an incomplete flag, curator-pending cross-references, and later
Tier 2 human ratification as expected pipeline states rather than defects by themselves.

The judge receives the exact document, acceptance case, and critic report. For Tier 1 it decides
`accept`, `reject`, or `escalate`. Only `accept` may trigger automatic merge. `reject`, `escalate`,
invalid output, or any unavailable stage requires human handling. For Tier 2 the judge recommends
`accept` or `reject`; human approval remains mandatory and automatic merge remains impossible.

The author, critic, and judge must use three distinct configured provider families when adversarial
review is enabled. The main LLM configuration supplies the author; dedicated critic and judge slots
supply the review models.

This amendment replaces ADR-011's dual-reviewer unanimity mechanism. It preserves ADR-011's review
tiers, fail-closed posture, cross-family independence, audit requirement, and unconditional Tier 2
human authority.

---

## Justification

Adversarial review is most legible when advocacy, challenge, and judgment are separate roles. The
author's known bias is useful because it forces the proposal to expose its claims and evidence before
the critic attacks them. The critic can respond to an actual defence rather than generating generic
negative review prose. A neutral judge can then distinguish a defeated proposal, a sound proposal,
and genuine uncertainty without asking either partisan role to abandon its assigned lens.

Three distinct families reduce shared training and alignment bias at each boundary. Although this is
operationally more demanding, allowing the author and judge or critic to share a family would weaken
the independence on which automated Tier 1 merge authority depends.

---

## Enforcement

- Processed documents must carry a bounded, non-empty acceptance case before automated review
- Acceptance cases are returned through the API and durable job state but excluded from published Markdown
- Critic and judge calls are sequential; the judge must receive both prior artefacts
- Enabled review requires three distinct provider families: main, critic, and judge
- Missing, unavailable, or invalid review artefacts fail closed to human handling
- Tier 1 auto-merge is possible only after a valid judge `accept` decision
- Tier 2 never auto-merges, regardless of the judge's recommendation
- Review comments record the acceptance case, challenge, adjudication, effective tier, and outcome
- Future changes to the adjudication roles or authority must amend or supersede this ADR

---

## Consequences

Positive:
- Review comments show a genuine proposal, rebuttal, and adjudication trail
- Borderline Tier 1 documents have an explicit escalation outcome
- Expected intermediate pipeline states no longer create shared false rejection grounds
- Human Tier 2 reviewers receive both arguments and a recommendation

Negative / trade-offs:
- Existing reviewer advocate configuration is removed and judge configuration is required
- Three-family deployments require an additional provider credential
- Review latency is the sum of critic and judge calls
- Editing a processed preview may make its authored case less persuasive; the judge must assess the case against the exact published document

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-011: Tiered review model](011-tiered-review-model.md)
- [ADR-019: Templates declare review tiers](019-template-declared-review-tiers.md)

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
