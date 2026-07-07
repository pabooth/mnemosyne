# ADR-012: Container-level decomposition of Mnemosyne

## Status

Draft

## Context

The original system design existed as a single mermaid/draw.io mind-map, grown organically while the ingestion architecture (five human intake routes, MCP as intake-only, the tiered review model in ADR-011) was being worked out. It served that purpose well, but on review it turned out to be doing three unrelated jobs with one set of boxes, arrows, and colours:

1. **Control flow** — what happens next (Classification → Augmentation → Trust Model → Publish).
2. **Actor/trust boundary** — who or what originated a piece of content (human, agentic loop, automated resolver).
3. **Deployment/ownership boundary** — what process code runs in, and who is responsible for it (mnemo-core, a standalone service, a third-party system).

Conflating these three axes is what made the diagram's colour scheme feel inconsistent under inspection: colours intended to mark deployment/ownership (e.g. red for "core logic") were sometimes applied based on control-flow or actor reasoning instead, and several nodes (`Self-Audit`, `Indexer`, the original `Human`-labelled agentic loop node) had colours that were leftover defaults rather than deliberate choices.

Before starting the next build phase (fleshing out `mnemo-core`, and building `mnemo-curator` and `mnemo-bot`), we need a diagram and a decision record that answers one question cleanly: **what actually has to be built and run as its own deployable, and what's the cost of skipping each optional one.** That is a container-level (C4) question, distinct from both the control-flow pipeline (already covered by ADR-011) and the intake-surface diagram (already covered by ADR-006).

## Decision

Decompose Mnemosyne into a container diagram with the following elements.

### Deployed services (we build, we run)

| Container | Required? | What's lost if skipped |
|---|---|---|
| `mnemo-core` | Required | The system does not function without it — it is the governance pipeline (classification, augmentation, dedup, adversarial review, trust model, publish) and now also owns indexing (see below). |
| `mnemo-ui` | Optional | Loses the one intake/read surface built for people who aren't already working in Git or an editor plugin. Every other intake route and both publish targets (MkDocs, Confluence) still function without it. |
| `mnemo-curator` | Optional | Loses active drift detection and inline issue resolution. Intake, review, and publish are unaffected — nothing is catching staleness, broken structure, or semantic gaps until a human happens to notice. |
| `mnemo-bot` | Optional | Loses conversational read (semantic search over the Vector DB) and conversational write. All other intake routes and publish targets are unaffected. It is architecturally distinct enough (long-running, conversational, its own technology stack) that a deployer may reasonably choose not to build it at all — this is a different kind of optionality from `mnemo-ui`/`mnemo-curator`, which are optional in *capability* but not in *technology*. |

### `mnemo-curator` internal shape

`mnemo-curator` absorbs what were previously drawn as two separate nodes, `Self-Audit`/`Inspector` and `Issue Resolver`:

- **Inspector** and **Resolver** are components inside the `mnemo-curator` container, not separate deployables — same relationship as `mnemo-core`'s internal pipeline stages are components of `mnemo-core`.
- Rationale for bundling: Resolver's only trigger was "an issue was just created" — bundling removes the need for a separate trigger mechanism (webhook or poll) entirely, since resolution simply becomes the next step in the same scheduled run rather than something a second process has to be notified about.
- Even with inline resolution, every finding is still written to the issue tracker before an inline fix is attempted — this is the crash-recovery/audit-trail boundary, not just the low-confidence path.
- A manual single-issue retry entrypoint (e.g. `--mode=retry --issue=<id>`) should exist alongside the scheduled full-sweep mode, so a specific stuck issue doesn't require waiting for or forcing a full sweep.
- The container was originally going to be named `mnemo-inspector`, but that name only reflects the read/reporting half of the job. Renamed to `mnemo-curator` to cover both inspection and correction. `Inspector` and `Resolver` remain as the component-level names inside it. The original `Self-Audit` label (same read-only bias) should be retired everywhere it appears — ADRs, Todoist tasks, docs — in favour of `mnemo-curator`.

### Indexing

Indexing is folded into `mnemo-core` rather than being its own container or a CI-pipeline step:

- Not a CI step, because that couples Vector DB freshness to a specific CI vendor's job succeeding, rather than to Git itself — a poor coupling for something other people will self-host on arbitrary Git hosts.
- Not a standalone service, because it is branch-free, stateless embed-and-write logic with no need for a persistent process between merges, and it needs the same embedding-model configuration as the rest of the system.
- Trigger shape: **on-demand primary path, with a low-frequency scheduled reconciliation pass as a fallback**, not a replacement. The reconciliation pass diffs "what's in the Repo at `main`" against "what's in the Vector DB" (by commit SHA or content hash) and only processes what's missing — it must not silently become a second full re-embed job. It also doubles as a monitoring signal: if it regularly finds gaps, the on-demand trigger is failing more than expected.
- The specific mechanism for calling it on-demand (webhook, direct call, queue) is an implementation decision, not an architectural one, and is deliberately left open here.

### First-party clients (we build the code, someone else's runtime hosts it)

- **Obsidian plugin** and **Chrome extension** (browser clipper) are built and maintained by us, but run inside Obsidian's and Chrome's processes respectively. There is no deployment decision for them the way there is for the containers above — a user installs them, nothing is stood up.
- No off-the-shelf equivalent exists for either: a generic clipper or note-taking plugin has no notion of Mnemosyne's MCP intake surface, Diátaxis classification, or the governance pipeline downstream. Bespoke build is the correct call, not a fallback from a failed search for an existing option.

### External tools (not ours, not our runtime)

- **LLM Desktop Client** and **Git-aware editor** (e.g. Tolaria) are entirely independent of Mnemosyne — not our code, not our runtime, no deployment story on our side at all. They integrate against surfaces we expose (MCP, Git) but are otherwise out of scope for our container diagram.

### External / commodity systems

- **Repo (Git)**, **Vector DB**, **MkDocs**, **Confluence** — genuinely third-party systems being integrated with, not proprietary logic.

### Actors

- **Human** — the general human actor, fanning out into the specific tools/containers listed above.
- **Agentic access** — the peer to Human at the actor level (originally drawn as `Agentic Loop Generation`, briefly relabelled `External process`). Represents an autonomous agentic loop or automation process that sits entirely outside the system as a consumer of it, submitting content directly to `mnemo-core` over MCP without going through any of the specific client tools. Renamed to "Agentic access" as the final label — precise about both the actor and the access path (MCP), and avoids "process," which read as one axis away from what it actually distinguishes (an actor type, not a runtime detail).

## Consequences

**What this gives us:**

- A deploy checklist: what's required (`mnemo-core`) versus optional, and what capability is lost by skipping each optional container — an answer the original mind-map could not give, because deployables, pipeline steps, and third-party systems were all drawn at the same visual weight.
- A blast-radius map: which pieces share a release cycle and failure domain (e.g. Inspector and Resolver, once bundled) and which are independent.
- A place for component-level diagrams to nest without competing for space with things that aren't part of that process — e.g. a future `mnemo-core` component diagram (Classification, Augmentation, Dedup, Adversarial Review, Trust Model) no longer has to share a canvas with `Repo` or `MkDocs`.

**What this deliberately does not cover:**

- Any control-flow/governance detail (Diátaxis classification, tier routing, the adversarial review gate) — that remains ADR-011's territory and belongs in a future `mnemo-core` component diagram, not here.
- The specific triggering mechanism for on-demand indexing (webhook format, direct call, queue) — implementation detail, left open by design.
- Failure-mode handling for the indexing reconciliation pass (fail loud vs. fail quiet on a bad merge) — open question, not yet decided.
- Whether `mnemo-curator`'s bundled design should itself be one package with two modes (`--mode=scan`, `--mode=resolve`, `--mode=retry`) versus something more granular — decided as one package for now; revisit if Inspector and Resolver's logic diverges enough to justify a split.

## Related ADRs

- ADR-006 (MCP as intake-only) — the intake surface this container diagram's `Rel` edges (API, MCP, Git, webhook) connect into.
- ADR-011 (tiered review model) — the control-flow axis this ADR deliberately excludes; unaffected by the container split, and expected to be diagrammed separately as a `mnemo-core` component diagram.
