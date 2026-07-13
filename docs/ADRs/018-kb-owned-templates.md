# ADR-018: Document templates live in the knowledge base and define the sub-label taxonomy

> **Status:** `Proposed`
> **Date:** 2026-07-13
> **Review date:** 2027-07-13

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-018 |
| **Title** | Document templates live in the knowledge base and define the sub-label taxonomy |
| **Status** | Proposed |
| **Date** | 2026-07-13 |
| **Review date** | 2027-07-13 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Amends** | — |
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

The pipeline shapes generated document bodies with templates, but today exactly one exists — a "standard" skeleton hardcoded as a Python string in `mnemo_core/pipeline/prompts.py`, keyed by `("reference", "standard")`. The classifier's sub-label taxonomy (13 names with descriptions and misclassification hints) is a second hardcoded blob in the same file. Adding or improving either means editing Python source and shipping a Mnemosyne release.

Both artifacts are really statements of *a knowledge base's* editorial conventions — what a runbook is, what sections a standard contains — and every deployment's answers differ. The people best placed to write them are the KB's curators, not Mnemosyne's developers, and the goal is that a person can see what a document type contains and improve it, or add a new one, without touching application code.

Mnemosyne distributes container images (image = code, per ADR-013's deployment model and the ADR-017 config boundary), so KB-specific content cannot be baked in at build time. ADR-003 fixes the four Diataxis types as the primary classification axes and leaves sub-labels as an organisational layer beneath them; ADR-005 requires all KB changes to arrive by reviewed pull request.

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
- Templates drift from the content they describe; a rename can't be reviewed with its consequences
- Per-path protection inside one repo (CODEOWNERS) achieves the same guard

#### Option 4: In the knowledge base repository itself *(chosen)*

A visible `templates/` directory beside the four Diataxis content folders, mirroring their structure: `templates/<type>/<sub-label>.md`.

**Pros:**
- A template is that KB's policy; it lives with, and versions with, the content it governs
- Edited by the same people who curate the KB, through the same reviewed-PR governance (ADR-005)
- CODEOWNERS on `/templates/` restricts who can approve template changes without a second repo

**Cons:**
- mnemo-core must fetch templates at runtime and handle the failure mode
- The indexer and curator must exclude `templates/` from content walks

### When templates are fetched

#### Option 1: Build time

Rejected outright: images are code and must work for any knowledge base (ADR-017's boundary); baked-in templates fossilise until rebuild.

#### Option 2: Per submission

**Cons:**
- Adds latency, rate-limit exposure, and a network failure mode to the hot path to pick up changes that happen rarely

#### Option 3: Once at startup *(chosen)*

**Pros:**
- One fetch, one failure mode, at the moment the operator is already watching
- Doubles as an end-to-end check of `GITHUB_REPO` and token validity before any document is accepted

**Cons:**
- Template changes need a service restart to take effect (an acceptable cost at their change frequency; a webhook-driven cache refresh through the existing GitHub intake is a possible future extension, not part of this decision)

### What defines the sub-label taxonomy

#### Option 1: Keep the hardcoded sub-label list; templates only shape bodies

**Pros:**
- Classification behaviour identical across all deployments

**Cons:**
- Adding a document type still requires a Mnemosyne release; the file set and the taxonomy can disagree

#### Option 2: The template set is the taxonomy *(chosen)*

Each template file declares its sub-label (filename), its parent Diataxis type (directory), and a description of when it applies (frontmatter). The classifier prompt is assembled from the fetched set. The four Diataxis types and their type-level classification rules remain fixed in code (ADR-003).

**Pros:**
- Adding a document type is a pure PR to the KB — no release, no code
- The taxonomy cannot drift from the template set because they are the same artifact

**Cons:**
- Classification quality now depends on KB-authored descriptions; a poor description degrades classification for that type
- Behaviour varies per KB, so evaluation must run against a deployment's template set

### Startup fetch failure behaviour

#### Option 1: Start degraded, retry in-process, report via `/ready`

**Cons:**
- "Up but degraded" is the most expensive state to operate: extra code to enter, extra signals to observe, extra reasoning to interpret
- Reimplements retry supervision the orchestrator already provides

#### Option 2: Fail fast and stop *(chosen)*

**Pros:**
- Two legible states: running correctly or stopped. Mnemosyne is an ingestion engine, not a read-path service — the KB serves readers regardless, and a submitter retries later
- The template fetch and the publish path share the same repo, token, and API: if the fetch fails, the service's core function is broken too
- Compose's `restart: unless-stopped` supervises retries with backoff for transient causes; persistent failure is visible as a restarting container with a clear log line

---

## Decision

1. Document templates live in the knowledge-base repository in a visible `templates/` directory beside the Diataxis content folders (under `DOCS_ROOT` when set): `templates/<type>/<sub-label>.md` — e.g. `templates/how-to/runbook.md`.
2. A template is Markdown with YAML frontmatter. The directory gives the Diataxis type, the filename gives the sub-label, and the frontmatter carries at minimum a `description` — the "when does a document count as this type" text that the classifier prompt includes verbatim. The body is the section skeleton for generated documents.
3. The fetched template set defines the sub-label taxonomy. The four Diataxis types and type-level classification rules stay fixed in code (ADR-003); sub-labels exist only as template files. An absent or empty `templates/` directory is a valid empty taxonomy: documents classify to bare Diataxis types with no sub-label.
4. mnemo-core fetches the template set once at startup. Any fetch failure — bad credentials, wrong repository, network — logs its cause and exits non-zero; the container restart policy supervises retries. There is no degraded mode.
5. mnemo-core ships zero embedded templates. The current standard template moves to an `examples/templates/` directory in the Mnemosyne repository for operators to copy into their KB. What is in the KB is the whole truth.
6. The indexer and curator exclude `templates/` from content walks; template files are never indexed, deduplicated against, or flagged by the curator.
7. Template protection is delegated to GitHub and must meet the repository's existing governance bar: template changes arrive only by pull request with passing checks and at least one human approval, a CODEOWNERS rule on `/templates/` names the required approvers, and the Mnemosyne service account must not be able to merge. Mnemosyne documents this; it does not enforce it.

---

## Justification

Templates and taxonomy are editorial policy, and policy belongs to the knowledge base it governs. Locating them in the KB gives the right authors (curators), the right change mechanism (reviewed PRs, per ADR-005), the right guard (CODEOWNERS), and the right versioning (alongside the content they shape) — all with machinery that already exists. Every alternative located the files with the wrong owner or created a parallel surface to operate.

Startup fetching is proportionate to how often templates change and converts the fetch into a free deploy-time credential check. Fail-stop follows from the service's role: an ingestion engine that cannot reach its knowledge base has lost its purpose, and a stopped container is a more honest and more operable statement of that than a running process in a degraded state.

Making the template set the taxonomy closes the gap between "what files exist" and "what the classifier knows" — they cannot disagree because they are one thing. The cost, classification quality depending on human-written descriptions, is judged acceptable: those descriptions are precisely the editorial knowledge the KB's curators hold, and the format makes their behavioural role explicit.

RAG over the template set was considered and rejected: retrieval solves candidate sets too large for a prompt, and a KB's template set (tens of files) fits whole. A future classification aid retrieving *similar existing documents* from the vector index (ADR-014) and hinting the classifier with their sub-labels is noted as a separate, optional enhancement — it is not part of this decision.

---

## Enforcement

- Templates and sub-label definitions must never be reintroduced as code or image content; `mnemo_core/pipeline/prompts.py` retains only the fixed Diataxis-type rules and the prompt-assembly logic
- New sub-label behaviour arrives only as template files in the KB; any feature needing more per-type knowledge extends the template frontmatter schema
- Content walks (indexer, curator) must exclude `templates/`; a test should pin this
- Startup must fail (non-zero exit, logged cause) when the template fetch fails; a test should pin the empty-taxonomy and fetch-failure behaviours
- Deployment documentation must cover the `templates/` layout, the CODEOWNERS guidance, and the restart-to-refresh behaviour
- Any proposal for degraded-mode startup, per-request fetching, or a separate templates repository should reference and supersede this ADR

---

## Consequences

Positive:
- Adding or improving a document type is an editorial PR to the KB — visible files, human review, no Mnemosyne release
- Each knowledge base gets its own taxonomy, matching real per-deployment requirements
- Startup validates KB connectivity and credentials before any document is accepted
- One less hardcoded blob in the pipeline; the template set and taxonomy cannot drift apart

Negative / trade-offs:
- Classification behaviour varies per KB and depends on the quality of KB-authored descriptions; the evaluation harness must run against a deployment's template set to be meaningful
- Template changes require a service restart to take effect
- mnemo-core gains a startup dependency on the KB being reachable — accepted deliberately as fail-fast
- KBs must adopt the reserved `templates/` directory name beside the Diataxis folders

---

## Related

- [ADR-003: Use Diataxis as the content classification taxonomy](003-diataxis-classification.md) — the fixed type layer this ADR builds beneath
- [ADR-005: Mandatory human review](005-human-review-governance.md) — the governance that template PRs inherit
- [ADR-007: KB layer pluggability](007-kb-layer-pluggability.md) — the KB access boundary the template fetch goes through
- [ADR-014: Pluggable vector-index layer](014-vector-index-pluggability.md) — context for the rejected template-RAG option and the noted future content-RAG hint
- [ADR-017: Instance directory](017-instance-directory.md) — the deployment/application config boundary that rules out build-time and instance-directory template storage

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
