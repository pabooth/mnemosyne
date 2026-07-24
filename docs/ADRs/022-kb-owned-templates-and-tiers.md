# ADR-022: KB-owned templates define the taxonomy and declare review tiers

> **Status:** `Accepted`
> **Date:** 2026-07-24
> **Review date:** 2027-07-24

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-022 |
| **Title** | KB-owned templates define the taxonomy and declare review tiers |
| **Status** | Accepted |
| **Date** | 2026-07-24 |
| **Review date** | 2027-07-24 |
| **Supersedes** | [ADR-018: KB-owned templates define the sub-label taxonomy](018-kb-owned-templates.md), [ADR-019: Templates declare the review tier of their document type](019-template-declared-review-tiers.md) |
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

The pipeline shapes generated document bodies with templates and classifies them against a sub-label
taxonomy. Both were originally hardcoded in `mnemo_core/pipeline/prompts.py`: one "standard" skeleton
keyed by `("reference", "standard")`, and a second blob of sub-label names with descriptions and
misclassification hints. Adding or improving either meant editing Python source and shipping a
Mnemosyne release.

Both artefacts are really statements of *a knowledge base's* editorial conventions — what a runbook
is, what sections a standard contains — and every deployment's answers differ. The people best placed
to write them are the KB's curators, not Mnemosyne's developers.

The review tier of a document was in the same position and was worse for being there. ADR-011 defined
Tier 2 in prose as "any document that defines, modifies, or affects the change process itself", that
prose was duplicated into the classifier prompt, and the classifying model assigned `review_tier` as
a per-document judgment. The tier boundary is the line between "no human saw this" and "a human must
approve this", and it was a probabilistic judgment made from prompt text owned by Mnemosyne's
developers. It also sat badly with the requirement — now carried by ADR-021 — that whatever defines
tier membership must itself be Tier 2 content, because prompt text is not governed as such.

Tier membership is a property of a document type: a runbook is Tier 1 because of what runbooks are,
not because of anything about one particular runbook. The taxonomy is therefore the natural home for
the tier boundary, and splitting the definition of a document type across two owners would be the
wrong outcome.

Mnemosyne distributes container images — image is code, per the ADR-017 configuration boundary — so
KB-specific content cannot be baked in at build time. ADR-003 fixes the four Diataxis types as the
primary classification axis and leaves sub-labels as an organisational layer beneath them.

This ADR supersedes ADR-018 and ADR-019 and states the whole template decision: where templates live,
when they are fetched, what they define, and what happens when the fetch fails.

---

## Considered Options

### Where templates live

#### Option 1: In the Mnemosyne repository, packaged into the image

**Pros:**
- Zero runtime fetching; versioned with the code

**Cons:**
- One global template set, but every deployment has different requirements
- Changing a template means a Mnemosyne release, not an editorial act

#### Option 2: In the instance directory (`$MNEMO_HOME/templates/`)

**Pros:**
- Instantly editable, no rebuild

**Cons:**
- Unversioned, unreviewed, invisible to everyone but the operator

#### Option 3: In a dedicated templates repository

**Pros:**
- Independent access control; could be shared across several KBs

**Cons:**
- A second operational surface (repo setting, token scope, fetch path, failure mode)
- Templates drift from the content they describe; a rename cannot be reviewed with its consequences
- Per-path protection inside one repo (CODEOWNERS) achieves the same guard

#### Option 4: In the knowledge base repository itself *(chosen)*

A visible `templates/` directory beside the four Diataxis content folders, mirroring their structure:
`templates/<type>/<sub-label>.md`.

**Pros:**
- A template is that KB's policy; it lives with, and versions with, the content it governs
- Edited by the same people who curate the KB, through the same reviewed-PR governance
- CODEOWNERS on `/templates/` restricts who can approve template changes without a second repo

**Cons:**
- mnemo-core must fetch templates at runtime and handle the failure mode
- The indexer and curator must exclude `templates/` from content walks

### When templates are fetched

#### Option 1: Build time

Rejected outright: images are code and must work for any knowledge base; baked-in templates fossilise
until rebuild.

#### Option 2: Per submission

**Cons:**
- Adds latency, rate-limit exposure, and a network failure mode to the hot path to pick up changes
  that happen rarely

#### Option 3: Once at startup *(chosen)*

**Pros:**
- One fetch, one failure mode, at the moment the operator is already watching
- Doubles as an end-to-end check of `GITHUB_REPO` and token validity before any document is accepted

**Cons:**
- Template changes need a service restart to take effect — acceptable at their change frequency; a
  webhook-driven cache refresh through the existing GitHub intake is a possible future extension, not
  part of this decision

### What defines the sub-label taxonomy

#### Option 1: Keep the hardcoded sub-label list; templates only shape bodies

**Pros:**
- Classification behaviour identical across all deployments

**Cons:**
- Adding a document type still requires a Mnemosyne release; the file set and the taxonomy can
  disagree

#### Option 2: The template set is the taxonomy *(chosen)*

Each template file declares its sub-label (filename), its parent Diataxis type (directory), and a
description of when it applies (frontmatter). The classifier prompt is assembled from the fetched
set. The four Diataxis types and their type-level rules remain fixed in code (ADR-003).

**Pros:**
- Adding a document type is a pure PR to the KB — no release, no code
- The taxonomy cannot drift from the template set because they are the same artefact

**Cons:**
- Classification quality depends on KB-authored descriptions; a poor description degrades
  classification for that type
- Behaviour varies per KB, so evaluation must run against a deployment's template set

### What determines a document's review tier

#### Option 1: Keep LLM-judged tiers

The classifier continues to assign `review_tier` from a prose description in its prompt.

**Pros:**
- No schema or code change
- Can, in principle, catch a governance document submitted under a factual sub-label

**Cons:**
- The most consequential line in the governance model becomes a per-document probabilistic judgment
- Tier policy lives in Mnemosyne's prompt text, owned by developers, invisible to and unreviewable by
  the KB's curators
- Prompt text is not governed as Tier 2 content, which the tier model requires of anything defining
  tier membership

#### Option 2: Map Diataxis type to tier in code

A fixed mapping such as "reference → tier-2, everything else → tier-1".

**Pros:**
- Deterministic; trivially simple

**Cons:**
- The four Diataxis types are the wrong axis: tier-2-ness tracks what a document *affects*, not its
  rhetorical shape — reference material is mostly routine factual content, while a review policy
  could classify as explanation or how-to
- One global policy for every deployment; changing it is a Mnemosyne release, repeating the
  misplacement this ADR corrects for descriptions

#### Option 3: Templates declare their tier in frontmatter *(chosen)*

Each template's frontmatter carries a `tier` field alongside `description`. The tier of a classified
document is looked up from its (type, sub-label) template. Absence of a declaration fails closed to
Tier 2.

**Pros:**
- Tier assignment becomes a deterministic lookup against a human-reviewed declaration
- Tier policy is per-KB editorial policy, owned by curators, changed by reviewed PR
- Satisfies the tier model's self-referential requirement structurally: template files are already
  protected by human-approved PRs, CODEOWNERS, and a service account that cannot merge
- Opening the auto-merge path for a document type becomes a positive, auditable decision, never a
  default

**Cons:**
- A governance document mis-classified into a Tier 1 sub-label inherits that sub-label's tier; the
  reviewers' escalation backstop must remain to catch this
- One more field for template authors to understand

### Startup fetch failure behaviour

#### Option 1: Start degraded, retry in-process, report via `/ready`

**Cons:**
- "Up but degraded" is the most expensive state to operate: extra code to enter, extra signals to
  observe, extra reasoning to interpret
- Reimplements retry supervision the orchestrator already provides

#### Option 2: Fail fast and stop *(chosen)*

**Pros:**
- Two legible states: running correctly, or stopped. Mnemosyne is an ingestion engine, not a
  read-path service — the KB serves readers regardless, and a submitter retries later
- The template fetch and the publish path share the same repo, token, and API: if the fetch fails,
  the service's core function is broken too
- Compose's `restart: unless-stopped` supervises retries with backoff for transient causes;
  persistent failure is visible as a restarting container with a clear log line

---

## Decision

1. Document templates live in the knowledge-base repository in a visible `templates/` directory
   beside the Diataxis content folders (under `DOCS_ROOT` when set): `templates/<type>/<sub-label>.md`
   — e.g. `templates/how-to/runbook.md`.
2. A template is Markdown with YAML frontmatter. The directory gives the Diataxis type, the filename
   gives the sub-label, and the frontmatter carries at minimum a `description` — the "when does a
   document count as this type" text that the classifier prompt includes verbatim — and a `tier`
   field with the value `tier-1` or `tier-2`. The body is the section skeleton for generated
   documents.
3. The fetched template set defines the sub-label taxonomy. The four Diataxis types and type-level
   classification rules stay fixed in code (ADR-003); sub-labels exist only as template files. An
   absent or empty `templates/` directory is a valid empty taxonomy: documents classify to bare
   Diataxis types with no sub-label.
4. The declared tier is canonical. The classifier does not assign `review_tier`; after
   classification, the pipeline sets it by lookup from the matched template. The classifying model
   has no influence over the tier, and the template's tier applies to every document classified to
   that (type, sub-label).
5. Absence fails closed. A template with no `tier` field is `tier-2`. A document classified to a bare
   Diataxis type with no sub-label, including under an empty taxonomy, is `tier-2`. Tier 1 exists
   only where a curator has positively declared it. An explicit but invalid `tier` value is a startup
   error (`TemplateFetchError`) — a typo of `tier-1` silently becoming `tier-2` would misstate the
   curator's reviewed intent.
6. The reviewers' tier recommendation under ADR-021 remains an escalation-only backstop: a reviewer
   recommending `tier-2` raises the effective tier of that contribution, and can never lower a
   declared `tier-2` to `tier-1`. The template declares the tier of the *sub-label*; the reviewers
   check that the *document* belongs there.
7. mnemo-core fetches the template set once at startup. Any fetch failure — bad credentials, wrong
   repository, network — logs its cause and exits non-zero; the container restart policy supervises
   retries. There is no degraded mode.
8. mnemo-core ships zero embedded templates. The standard template lives in `examples/templates/` in
   the Mnemosyne repository for operators to copy into their KB. What is in the KB is the whole
   truth.
9. The indexer and curator exclude `templates/` from content walks; template files are never indexed,
   deduplicated against, or flagged by the curator.
10. Template protection is delegated to GitHub and must meet the repository's existing governance
    bar: template changes arrive only by pull request with passing checks and at least one human
    approval, a CODEOWNERS rule on `/templates/` names the required approvers, and the Mnemosyne
    service account must not be able to merge. Mnemosyne documents this; it does not enforce it.

---

## Justification

Templates, taxonomy, and tier policy are editorial policy, and policy belongs to the knowledge base it
governs. Locating them in the KB gives the right authors (curators), the right change mechanism
(reviewed PRs), the right guard (CODEOWNERS), and the right versioning (alongside the content they
shape) — all with machinery that already exists. Every alternative located the files with the wrong
owner or created a parallel surface to operate.

Making the template set the taxonomy closes the gap between "what files exist" and "what the
classifier knows" — they cannot disagree because they are one thing. The cost, classification quality
depending on human-written descriptions, is acceptable: those descriptions are precisely the
editorial knowledge the KB's curators hold, and the format makes their behavioural role explicit.

Declaring the tier in the same artefact follows the same argument, and one further one that is
decisive. ADR-021 requires that whatever defines tier membership is itself Tier 2 content —
unconditionally human-approved, unmergeable by the pipeline. Template files under this ADR's
protection already have exactly those properties, so declaring tiers there satisfies the
constitutional requirement with machinery that already exists. It also keeps the whole definition of
a document type — what it is (`description`), what it looks like (body), and how much trust its
contributions get (`tier`) — in one reviewed artefact with one owner. A line as consequential as the
tier boundary should be a definition, not a judgment: deterministic, versioned, reviewed by the people
accountable for the KB, and identical for every document of the same type.

Fail-closed defaults preserve the tier model's posture at every gap: missing declarations,
sub-label-less classifications, and empty taxonomies all land on mandatory human review. A deployment
that ignores the field entirely gets uniform-human-review behaviour; each `tier: tier-1` declaration
is then a deliberate, reviewed widening of automation — a trust ratchet operated by curators, not a
default operated by omission.

Startup fetching is proportionate to how often templates change and converts the fetch into a free
deploy-time credential check. Fail-stop follows from the service's role: an ingestion engine that
cannot reach its knowledge base has lost its purpose, and a stopped container is a more honest and
more operable statement of that than a running process in a degraded state.

RAG over the template set was considered and rejected: retrieval solves candidate sets too large for a
prompt, and a KB's template set — tens of files — fits whole. A future classification aid retrieving
*similar existing documents* from the vector index (ADR-014) and hinting the classifier with their
sub-labels is noted as a separate, optional enhancement, not part of this decision.

---

## Enforcement

- Templates, sub-label definitions, and tier policy must never be reintroduced as code or image
  content; `mnemo_core/pipeline/prompts.py` retains only the fixed Diataxis-type rules and the
  prompt-assembly logic
- New sub-label behaviour arrives only as template files in the KB; any feature needing more per-type
  knowledge extends the template frontmatter schema
- `parse_template` must parse and validate `tier`, defaulting to `tier-2` when absent and raising
  `TemplateFetchError` on any value other than `tier-1` or `tier-2`; tests pin both behaviours
- The classifier prompt must not mention review tiers; `review_tier` on a processed document is
  assigned only by template lookup, and a test pins that the LLM's output cannot influence it
- Documents with no matching template must receive `tier-2`; a test pins this
- The reviewers' tier recommendation must remain escalation-only: it may raise `tier-1` to `tier-2`,
  never the reverse
- Example templates in `examples/templates/` must all carry an explicit `tier`, and their README must
  document the field and the fail-closed default
- Content walks (indexer, curator) must exclude `templates/`; a test should pin this
- Startup must fail with a non-zero exit and a logged cause when the template fetch fails; tests
  should pin the empty-taxonomy and fetch-failure behaviours
- Deployment documentation must cover the `templates/` layout, the CODEOWNERS guidance, and the
  restart-to-refresh behaviour
- Any proposal for degraded-mode startup, per-request fetching, a separate templates repository, or a
  mechanism that lets content other than a reviewed template file determine a document's tier must
  supersede this ADR

---

## Consequences

Positive:
- Adding or improving a document type is an editorial PR to the KB — visible files, human review, no
  Mnemosyne release
- Each knowledge base gets its own taxonomy and its own tier policy, matching real per-deployment
  requirements
- Tier assignment is deterministic, auditable, and identical for every document of a type
- The auto-merge path is opt-in per document type, giving deployments a gradual trust ratchet from
  full human review to selective automation
- Startup validates KB connectivity and credentials before any document is accepted
- One less hardcoded blob in the pipeline, and one fewer judgment the classifier prompt asks of the
  model

Negative / trade-offs:
- Classification behaviour varies per KB and depends on the quality of KB-authored descriptions; the
  evaluation harness must run against a deployment's template set to be meaningful
- Mis-classification into a Tier 1 sub-label now matters more; the reviewers' escalation backstop and
  human vigilance over template descriptions carry that risk
- Template authors must understand a second frontmatter field, and its absence silently — by design —
  disables auto-merge for that type
- Template and tier changes require a service restart to take effect
- mnemo-core gains a startup dependency on the KB being reachable, accepted deliberately as fail-fast
- KBs must adopt the reserved `templates/` directory name beside the Diataxis folders

---

## Related

- [ADR-003: Use Diataxis as the content classification taxonomy](003-diataxis-classification.md) — the fixed type layer this ADR builds beneath
- [ADR-007: KB layer pluggability](007-kb-layer-pluggability.md) — the KB access boundary the template fetch goes through
- [ADR-014: Pluggable vector-index layer](014-vector-index-pluggability.md) — context for the rejected template-RAG option and the noted future content-RAG hint
- [ADR-017: Instance directory](017-instance-directory.md) — the deployment/application config boundary that rules out build-time and instance-directory template storage
- [ADR-021: Tiered review with adversarial adjudication and author rebuttal](021-tiered-adversarial-review.md) — the tiers this ADR's declarations feed, and the escalation backstop

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
