# ADR-021: Tiered review with adversarial adjudication and author rebuttal

> **Status:** `Accepted`
> **Date:** 2026-07-24
> **Review date:** 2027-07-24

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-021 |
| **Title** | Tiered review with adversarial adjudication and author rebuttal |
| **Status** | Accepted |
| **Date** | 2026-07-24 |
| **Review date** | 2027-07-24 |
| **Supersedes** | [ADR-011: Tiered review model for KB contributions](011-tiered-review-model.md), [ADR-020: Adjudicate an authored case against an adversarial challenge](020-adversarial-adjudication.md) |
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

ADR-005 required a human to approve every KB contribution. ADR-011 superseded it with a tiered model:
standard content may merge on automated agreement, while governance and constitutional content always
requires human approval. That tiering remains correct and is carried forward here unchanged.

The automated gate beneath it has not been correct. ADR-011 specified two cross-family reviewers with
deliberately opposed prompts and treated their agreement or disagreement as the gate. In operation
both models independently judged the same document without seeing one another's reasoning, which
produced two asymmetric inspections rather than an adversarial argument, and made each model both
counsel and judge. ADR-020 replaced that with three roles: the main processing model authors the
document and an evidence-based acceptance case, a cross-family critic challenges that case, and a
third-family judge adjudicates.

The three-role sequence corrected the original defect, but it closes the record at the challenge, and
two problems follow.

First, the author never answers. A blocking concern founded on a misreading of the document reaches
the judge unopposed, and the judge must dispose of it from the critic's material alone. The author is
the only party that knows what the document was intended to assert and why a passage is phrased as it
is. ADR-020 gives it one turn to anticipate objections before it has seen any, and no turn at all
once the real objections exist.

Second, the judge's output is not bound to the dispute it is adjudicating. The judge report carries a
free-text verdict and a free-text concerns list, produced independently of one another and of the
critic's concerns. ADR-020 requires the judge not to introduce objections the critic did not raise
and to reject only on an upheld blocking concern, but expresses both as prompt instructions over
unstructured output. Nothing detects a judge that returns `accept` alongside upheld concerns, that
rewords a concern into a different one, or that supplies an objection of its own. Judges drifting
outside the record has been observed in operation, and it is the failure mode with the most direct
route to an unwarranted automatic merge.

This ADR supersedes both ADR-011 and ADR-020, and states the review model in full: the tiers and
their exit conditions carried forward from ADR-011, the role separation carried forward from ADR-020,
and the rebuttal round and bounded adjudication decided here.

---

## Considered Options

The tier model itself is not reopened; the options below concern the automated gate beneath it.

### Option 1: Retain ADR-020's three-role sequence

Keep author, critic, and judge as they stand, and address unanswered misreadings by tuning the
critic's prompt toward fewer, better-substantiated blocking concerns.

**Pros:**
- No new model call, latency, or contract change
- Keeps the review sequence at three roles

**Cons:**
- Prompt calibration cannot supply the authorial intent only the author holds
- Leaves the judge's output unbound to the critic's concerns, which is the more serious defect
- Trades false rejections for false acceptances rather than removing either

### Option 2: Add a critic surrebuttal after the author's response

Let the author answer, then let the critic answer the answer.

**Pros:**
- Each party gets the last word in turn

**Cons:**
- No principled place to stop; every additional round has the same argument behind it
- Doubles the contested-path cost for diminishing returns
- The judge exists precisely to close the record; a surrebuttal delegates that job back to a partisan

### Option 3: Multiple judges, or a judge permitted to review independently

Resolve uncertainty by adding judges, or by letting the judge raise objections of its own.

**Pros:**
- More inspection surface per contribution

**Cons:**
- ADR-011 already established that independent verdicts are not an adversarial argument
- A judge that raises objections is a third partisan with decision authority, which is the exact
  conflation ADR-020 removed
- Cost scales with no corresponding gain in legibility

### Option 4: Author rebuttal in which a conceded concern binds the outcome

Add the rebuttal round, and make the author's admission of a blocking concern mechanically
determinative so that the outcome does not depend on trusting the judge at that point.

**Pros:**
- The admission is machine-checkable and cannot be overlooked by the judge
- Removes one point of judge discretion from the automatic-merge path

**Cons:**
- Admission becomes dominated: disputing is never worse, so a rational author never admits anything
  and the field records nothing
- Converts model agreeableness under confident challenge directly into rejections — a firmly worded
  but incorrect blocking concern can extract an admission the document does not warrant
- Removes the judge's authority to find that a concern was never blocking in the first place

### Option 5: Author case, challenge, author rebuttal, bounded adjudication *(chosen)*

Keep the author, critic, and judge roles and their family separation; add one author round answering
the critic's blocking concerns by reference; require the judge to dispose of each of those concerns
and derive the verdict from those dispositions; give every artefact in the record a stable identity.
The judge remains the sole decision-maker.

**Pros:**
- The author answers real objections instead of anticipated ones
- The judge cannot reach outside the record, because the output has no free-form verdict for an
  outside objection to occupy
- Verdict and reasoning can no longer contradict each other
- The author's declining to argue stays a signal rather than becoming a sentence

**Cons:**
- A fourth sequential model call on contested contributions
- The critic and judge report contracts change, and review results stored under ADR-020 are not
  comparable
- The author speaks last, so the adjudication must resist recency by construction

---

## Decision

### Review tiers

KB contributions are classified into two tiers. Adversarial review is the universal mechanism applied
to both; the exit condition after review differs by tier.

**Tier 1 — standard content.** Factual KB content: how-to documents, tutorials, reference material,
explanations, terminology, cross-references, and lessons-learnt entries captured from agent
operation. A Tier 1 contribution may be approved and merged without human sign-off when, and only
when, adversarial review produces an `accept`. Human review remains available at any time; this tier
sets the minimum gate, not a ceiling.

**Tier 2 — governance and constitutional content.** Any document that defines, modifies, or affects
the change process itself: ADRs, pipeline configuration, review policy, trust tier definitions,
enforcement rules, and any document that determines what belongs in Tier 2. Adversarial review is
applied and produces a recommendation, but human approval is mandatory regardless of the outcome.
This requirement is unconditional and is not configurable.

A document's tier is declared by its template under ADR-022 and is never judged by a model. Anything
without a declaration fails closed to Tier 2. No stage of review may lower a tier; a reviewer's tier
recommendation may raise the effective tier only, as the backstop against a governance document
classified into a Tier 1 sub-label.

**Governance gap identification.** As Mnemosyne operates agentically it will encounter scenarios no
existing governance covers. Agents may surface these as issues flagging a governance gap. A human
determines whether to draft the corresponding ADR or to ask the agent to propose a draft; as trust in
the pipeline matures, agents may propose governance documents directly. Such proposals are always
Tier 2 and follow the mandatory human review path.

### The record

Adversarial review is a four-stage record: an authored case, a cross-family challenge, an author
rebuttal, and a bounded adjudication. Review runs after the pull request exists and never blocks
publication.

**The author's case.** The main processing model produces both the processed document and an
evidence-based `acceptance_case` identifying the document's principal claims, supporting evidence,
fitness for its Diataxis purpose, anticipated objections, limitations, and expected pipeline work. It
is a bounded structured object with separate `claims`, `evidence`, `diataxis_fit`,
`anticipated_objections`, `limitations`, and `pipeline_pending` fields. Structured fields prevent the
defence from becoming an unbounded persuasive essay and give the critic distinct evidence and
objection material to test. The acceptance case is review metadata: it travels through the API and
durable job state and is never published as knowledge-base content.

**The challenge.** After the PR is created, the critic receives the exact proposed document and its
acceptance case. It produces a rejection case attempting to establish material correctness, safety,
provenance, governance, context, or document-fitness defects, and distinguishes blocking from
non-blocking concerns. It treats proposed status, an incomplete flag, curator-pending
cross-references, and later Tier 2 human ratification as expected pipeline states rather than defects
by themselves.

Blocking concerns are an ordered, bounded list with stable positions. The bound is small enough to
force the critic to prioritise its strongest grounds rather than emit an undisposable inventory.
Non-blocking concerns are advisory, are recorded for the human reader, and can never affect the
verdict.

**The rebuttal.** The author receives the exact published document, its own acceptance case, and the
critic's challenge, and answers the critic's blocking concerns. The rebuttal is performed by the main
provider family in a fresh call; it introduces no fourth family and no additional credential.

The rebuttal answers concerns by reference. For each blocking concern it addresses, the author gives
one of two stances:

- **dispute** — the author argues the concern is unfounded, overstated, or not blocking, and states
  why from the document and its evidence.
- **no contest** — the author declines to argue the concern and adds nothing to the record.

A concern the rebuttal does not address is undefended and is disposed of on the critic's material
alone, exactly as a no-contested concern is. The stances differ in what they record, not in what they
cause: an author that no-contests most concerns is working as designed, while an author that silently
omits most of them is malfunctioning, and the two are distinguishable only if declining is explicit.

Neither stance decides anything. A no-contested concern may still be found unsubstantiated or
non-blocking by the judge.

The rebuttal defends the exact published document, which may have been edited by a human after
preview and may therefore differ from what the author drafted. The author may not amend the document
during review; a defect it accepts is resolved by the judge's decision and the human handling that
follows, not by revision within the round.

The rebuttal is skipped when the critic raises no blocking concerns, because there is nothing to
answer.

**The adjudication.** The judge receives the document, acceptance case, challenge, and rebuttal. It
adjudicates that record and does not perform another open-ended review. It returns a disposition for
every blocking concern the critic raised, identified by position, as one of:

- **upheld** — the concern is substantiated and blocking
- **dismissed** — the concern is unfounded, or is not a blocking defect
- **unresolved** — the concern is plausible but cannot be settled from the record

The verdict is derived from those dispositions in code rather than stated by the judge:

- any concern upheld → **reject**
- no concern upheld and any unresolved → **escalate**
- no concern upheld or unresolved → **accept**

Dispositions that do not correspond to the critic's blocking concerns, and reports that omit a
concern, are invalid. The judge has no free-text verdict field and no channel for an objection the
critic did not raise.

A rebuttal argument that misrepresents the document or the concern it answers weighs against the
author's case rather than counting as neutral.

### Authority and failure

For Tier 1, a derived `accept` is the only outcome that may trigger automatic merge. `reject`,
`escalate`, invalid output at any stage, or any unavailable stage requires human handling. For Tier 2
the derived outcome is a recommendation to the mandatory human reviewer; human approval remains
unconditional and automatic merge remains impossible.

The author, critic, and judge must use three distinct configured provider families when adversarial
review is enabled. The main LLM configuration supplies the author for both the case and the rebuttal;
dedicated critic and judge slots supply the review models. Reviewer model slots are configured
through the pluggable LLM layer (ADR-004); specific model identities are operational decisions, not
architectural ones.

### Record integrity

Every artefact in the record — document, acceptance case, challenge, rebuttal — must be attributable
to the party that produced it and must not be forgeable by another party. Submitted content is
untrusted and must not be able to present itself as a challenge, a rebuttal, an adjudication, or an
instruction to a reviewing model. The mechanism is an implementation concern; the requirement is not.

---

## Justification

ADR-011's tiering was correct and remains so. Uniform human review does not scale as contribution
volume grows with agentic operation, and at scale it incentivises rubber-stamping — approval in name
only, which is worse than a well-designed automated gate because it creates the appearance of
oversight without its substance. At the same time a routine reference update and a change to review
policy are not equivalent risks. The constitutional protection for Tier 2 is not merely a quality
gate: allowing automated review to be the final authority over governance documents would permit the
review mechanism to erode the constraints it operates under, and the constraint must be
self-referential, which is why the definition of tier membership is itself Tier 2 content.

Adversarial review is most legible when advocacy, challenge, and judgment are separate roles, and
that separation — ADR-020's contribution — is retained here unchanged. The author's known bias is
useful because it forces the proposal to expose its claims and evidence before the critic attacks
them; the critic can respond to an actual defence rather than generating generic negative review
prose; a neutral judge can then distinguish a defeated proposal, a sound proposal, and genuine
uncertainty without asking either partisan role to abandon its assigned lens. Three distinct families
reduce shared training and alignment bias at each boundary, and allowing the author to share a family
with the critic or judge would weaken the independence on which automated Tier 1 merge authority
depends.

The rebuttal is the smallest change that closes the gap that model left. The author holds information
no other party has — what the document was meant to assert — and ADR-020 asked it to spend that
information anticipating objections before any existed. One responsive round converts the acceptance
case from a guess about the challenge into an answer to it, and it costs a model call only on
contributions the critic has actually contested.

Giving the author the last word is safe only because the adjudication is bounded. If the judge
returned free prose and a verdict token, speaking last would be an advantage, and recency is a real
effect. Requiring a disposition for each concern by position removes the advantage: the author's
argument is weighed against the concern it answers rather than against the record as a whole, and the
judge must account for every ground the critic raised whether or not the author addressed it.

Deriving the verdict rather than accepting one is the change that most directly protects automatic
merge authority. Under ADR-020 the verdict and the reasoning are produced independently and can
disagree without detection; a judge that upholds three concerns and returns `accept` will merge a
rejected document. Derivation makes that state unrepresentable. It also removes the surface that
judge scope-drift needs: an objection the critic never raised has nowhere to go, because dispositions
are keyed to the critic's concerns and there is no other field to write in.

The rejected binding-concession option is worth recording because its appeal is real. Making an
admission determinative looks like it strengthens the gate, and it does remove one point of judge
discretion. But it prices admission at rejection, which makes disputing weakly dominant in every
branch and guarantees the author never admits anything — the field would record nothing. Worse, it
converts a known model behaviour into an outcome: these models concede under confident challenge
regardless of whether the challenge is correct, so a firmly worded but wrong blocking concern would
extract a fatal admission the document does not warrant. Declining to argue must remain a
declination. The judge decides whether the concern was ever blocking, which is the question the
author cannot answer about its own work.

Record integrity is stated here rather than left to implementation because the record is what carries
merge authority. Every artefact after the first is derived from untrusted submitted content, and the
number of parties whose text reaches a decision-making model rises from two to three under this ADR.
A submission that can forge a challenge or address the judge directly defeats every other constraint
in this document.

---

## Enforcement

- The tier of a contribution must be determined at PR creation time from its template declaration
  (ADR-022) and recorded in the PR metadata; no model output may set or lower it
- The document defining tier membership is itself Tier 2; changes to tier definitions require human
  review
- Processed documents must carry a bounded, non-empty acceptance case before automated review
- Acceptance cases are returned through the API and durable job state but excluded from published
  Markdown
- Critic blocking concerns are an ordered list bounded to a small maximum, enforced at validation
- Contributions with at least one critic blocking concern must carry a rebuttal before adjudication;
  a missing or invalid rebuttal escalates to human review
- Rebuttal entries must reference existing critic blocking concerns by position and carry a stance of
  `dispute` or `no contest`; unaddressed concerns are permitted and treated as undefended
- Judge reports must dispose of every critic blocking concern by position and must carry no free-text
  verdict; incomplete, unmatched, or malformed dispositions escalate
- The verdict is computed from the dispositions in code and is never taken from model output
- Critic, rebuttal, and judge calls are sequential; each stage must receive all prior artefacts
- Review material passed to any reviewing model must delimit each artefact so that submitted content
  cannot present itself as another party's contribution
- Enabled review requires three distinct provider families: main, critic, and judge; same-family
  pairing must be rejected at configuration time
- Missing, unavailable, or invalid review artefacts fail closed to human handling
- Tier 1 auto-merge is possible only after a derived `accept`
- Tier 2 never auto-merges, regardless of the derived outcome
- Review comments record the acceptance case, challenge, rebuttal, per-concern dispositions,
  effective tier, and outcome
- The pipeline service account must not have merge permissions for Tier 2 PRs under any circumstances
- Future changes to the tiers, the adjudication roles, the rounds, or the authority must supersede
  this ADR

---

## Consequences

Positive:
- Standard KB contributions scale without creating a rubber-stamp bottleneck
- Governance and constitutional documents retain unconditional human oversight
- Review comments show a complete claim, challenge, answer, and per-concern disposition trail
- Blocking concerns founded on misreadings can be answered by the only party able to answer them
- The judge's verdict and its reasoning cannot contradict each other
- Judge scope-drift has no field to occupy, rather than being prohibited by instruction alone
- Declining to argue remains distinguishable from failing to argue, and neither is a sentence
- Borderline Tier 1 documents retain an explicit escalation outcome
- Human Tier 2 reviewers receive the full record and a derived recommendation

Negative / trade-offs:
- Contested contributions cost a fourth sequential model call and the latency that implies
- The critic and judge report contracts change; review results stored under ADR-020 are not
  comparable to results produced under this ADR
- An author-family outage now blocks review as well as processing, because the rebuttal shares the
  main model configuration
- Bounding the critic's blocking concerns discards genuine low-priority grounds it might otherwise
  have raised
- The author speaks last, and the protection against that is structural rather than positional
- A judge that misapplies a disposition still decides the outcome; derivation constrains the shape of
  the decision, not its quality
- Cross-family independence requires access to models from three distinct provider families
- Tier 2 mandatory human review remains a bottleneck for governance changes; governance evolution is
  intentionally slow
- Editing a processed preview may make its authored case less persuasive; the judge assesses the case
  against the exact published document

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-005: AI must not contribute to the knowledge base without human review](005-human-review-governance.md) — the uniform-review position ADR-011 replaced
- [ADR-022: KB-owned templates define the taxonomy and declare review tiers](022-kb-owned-templates-and-tiers.md) — how a document's tier is determined

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
