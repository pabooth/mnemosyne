# ADR-019: Templates declare the review tier of their document type

> **Status:** `Proposed`
> **Date:** 2026-07-14
> **Review date:** 2027-07-14

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-019 |
| **Title** | Templates declare the review tier of their document type |
| **Status** | Proposed |
| **Date** | 2026-07-14 |
| **Review date** | 2027-07-14 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Amends** | [ADR-011: Tiered review model](011-tiered-review-model.md), [ADR-018: KB-owned templates](018-kb-owned-templates.md) *(on acceptance)* |
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

ADR-011 established the tiered review model: Tier 1 contributions may merge automatically when both adversarial reviewers accept; Tier 2 contributions always require human approval. It defined the tiers in prose — Tier 2 is "any document that defines, modifies, or affects the change process itself" — and required that the document defining tier membership be itself Tier 2 content.

Today that prose is the only definition. It is duplicated into the classifier prompt, and the classifying LLM assigns `review_tier` as a judgment call on every document. The adversarial reviewers each make the same judgment again (`recommended_tier`), and any reviewer saying Tier 2 escalates the effective tier. There is no deterministic ground truth: a document that the classifier and both reviewers all mis-judge as Tier 1 has no independent check, and the tier boundary itself lives in prompt text owned by Mnemosyne's developers rather than by the knowledge base it governs.

ADR-018 (currently Proposed) establishes that the KB's template set *is* the sub-label taxonomy: each `templates/<type>/<sub-label>.md` file is the authoritative statement of what that document type means, protected by branch protection and a CODEOWNERS rule that the pipeline's service account cannot bypass. Tier membership is a property of a document type — a runbook is Tier 1 *because of what runbooks are*, not because of anything about one particular runbook. The taxonomy is therefore the natural home for the tier boundary, and leaving it in prompt prose while the rest of the taxonomy moves to the KB would split the definition of a document type across two owners.

---

## Considered Options

### Option 1: Keep LLM-judged tiers (status quo)

The classifier continues to assign `review_tier` from a prose description in its prompt.

**Pros:**
- No schema or code change
- Can, in principle, catch a governance document submitted under a factual sub-label

**Cons:**
- The tier boundary — the most consequential line in the governance model — is a per-document probabilistic judgment, not a definition
- Tier policy lives in Mnemosyne's prompt text, owned by developers, invisible to and unreviewable by the KB's curators
- Sits awkwardly with ADR-011's requirement that tier membership definitions are Tier 2 content: prompt text is not governed as such

### Option 2: Map Diataxis type to tier in code

A fixed mapping such as "reference → tier-2, everything else → tier-1".

**Pros:**
- Deterministic; trivially simple

**Cons:**
- The four Diataxis types are the wrong axis: tier-2-ness tracks what a document *affects* (the change process), not its rhetorical shape — reference material is mostly routine factual content, while a review policy could classify as explanation or how-to
- One global policy for every deployment; changing it is a Mnemosyne release, repeating the misplacement ADR-018 corrects for descriptions

### Option 3: Templates declare their tier in frontmatter *(chosen)*

Each template's frontmatter carries a `tier` field alongside `description`. The tier of a classified document is looked up from its (type, sub-label) template. Absence of a declaration fails closed to Tier 2.

**Pros:**
- Tier assignment becomes a deterministic lookup against a human-reviewed declaration, not a per-document model judgment
- Tier policy is per-KB editorial policy, owned by the curators, changed by reviewed PR — the same ownership correction ADR-018 makes for the taxonomy
- Satisfies ADR-011's self-referential requirement structurally: template files are already protected by human-approved PRs, CODEOWNERS, and a service account that cannot merge, so the definition of tier membership is automatically governed as Tier 2 content
- Opening the auto-merge path for a document type becomes a positive, auditable decision (a reviewed PR adding `tier: tier-1`), never a default

**Cons:**
- A governance document mis-classified into a Tier 1 sub-label inherits that sub-label's tier; the reviewers' escalation backstop must remain to catch this
- One more field for template authors to understand

---

## Decision

1. The template frontmatter schema (ADR-018) gains a `tier` field with the values `tier-1` and `tier-2`, matching ADR-011's tiers. The template's tier applies to every document classified to that (type, sub-label).
2. The declared tier is canonical. The classifier no longer assigns `review_tier`; after classification, the pipeline sets it by lookup from the matched template. The classifying model has no influence over the tier.
3. Absence fails closed. A template with no `tier` field is `tier-2`. A document classified to a bare Diataxis type with no sub-label (including under an empty taxonomy) is `tier-2`. Tier 1 exists only where a curator has positively declared it.
4. An explicit but invalid `tier` value is a startup error (`TemplateFetchError`), consistent with ADR-018's fail-fast posture — a typo of `tier-1` silently becoming `tier-2` would misstate the curator's reviewed intent.
5. The adversarial reviewers' `recommended_tier` remains, as an escalation-only backstop (ADR-011): either reviewer recommending `tier-2` raises the effective tier of that contribution to `tier-2`. It can never lower a declared `tier-2` to `tier-1`. This is the check on classification error — the template declares the tier of the *sub-label*; the reviewers check that the *document* belongs there.

---

## Justification

The tier boundary is the line between "no human saw this" and "a human must approve this". A line that consequential should be a definition, not a judgment: deterministic, versioned, reviewed by the people accountable for the KB, and identical for every document of the same type. Frontmatter declaration achieves all four; the status quo achieves none.

The deciding argument over any code-level mapping is governance placement. ADR-011 requires that whatever defines tier membership is itself Tier 2 content — unconditionally human-approved, unmergeable by the pipeline. Template files under ADR-018's protection already have exactly those properties, so declaring tiers there satisfies the constitutional requirement with machinery that already exists. It also keeps the whole definition of a document type — what it is (`description`), what it looks like (body), and how much trust its contributions get (`tier`) — in one reviewed artifact with one owner.

Fail-closed defaults preserve ADR-011's posture at every gap: missing declarations, sub-label-less classifications, and empty taxonomies all land on mandatory human review. A deployment that ignores the field entirely gets ADR-005-equivalent behaviour; each `tier: tier-1` declaration is then a deliberate, reviewed widening of automation — a trust ratchet operated by curators, not a default operated by omission.

---

## Enforcement

- `parse_template` must parse and validate `tier`, defaulting to `tier-2` when absent and raising `TemplateFetchError` on any value other than `tier-1` or `tier-2`; tests pin both behaviours
- The classifier prompt must not mention review tiers; `review_tier` on a processed document is assigned only by template lookup, and a test pins that the LLM's output cannot influence it
- Documents with no matching template (no sub-label, or an empty taxonomy) must receive `tier-2`; a test pins this
- The reviewers' `recommended_tier` escalation in the adversarial review must remain escalation-only: it may raise `tier-1` to `tier-2`, never the reverse
- Example templates in `examples/templates/` must all carry an explicit `tier`, and their README must document the field and the fail-closed default
- Any future mechanism that would let content other than a reviewed template file determine a document's tier must reference and supersede this ADR

---

## Consequences

Positive:
- Tier assignment is deterministic, auditable, and identical for every document of a type
- Tier policy is per-KB and curator-owned, changed only by human-approved PR — structurally satisfying ADR-011's self-reference requirement
- The auto-merge path is opt-in per document type, giving deployments a gradual trust ratchet from full human review to selective automation
- One fewer judgment the classifier prompt asks of the model

Negative / trade-offs:
- Mis-classification into a Tier 1 sub-label now matters more; the reviewers' escalation backstop and human vigilance over template descriptions carry that risk
- Template authors must understand a second frontmatter field, and its absence silently (by design) disables auto-merge for that type
- Tier changes take effect only on service restart, like all template changes (ADR-018)

---

## Related

- [ADR-011: Tiered review model for KB contributions](011-tiered-review-model.md) — defines the tiers and the self-referential governance requirement this ADR satisfies
- [ADR-018: KB-owned templates define the sub-label taxonomy](018-kb-owned-templates.md) — the frontmatter schema and protection regime this ADR extends
- [ADR-005: Mandatory human review](005-human-review-governance.md) — the fail-closed posture this ADR's defaults preserve
- [ADR-003: Diataxis classification](003-diataxis-classification.md) — the fixed type layer beneath the sub-label taxonomy

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
