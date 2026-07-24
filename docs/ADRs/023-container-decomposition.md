# ADR-023: Decompose Mnemosyne into deployed services, clients, and external systems

> **Status:** `Accepted`
> **Date:** 2026-07-24
> **Review date:** 2027-07-24

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-023 |
| **Title** | Decompose Mnemosyne into deployed services, clients, and external systems |
| **Status** | Accepted |
| **Date** | 2026-07-24 |
| **Review date** | 2027-07-24 |
| **Supersedes** | [ADR-012: Container-level decomposition](012-container-decomposition.md), [ADR-016: Extract edge routing into mnemo-proxy](016-standalone-proxy-container.md) |
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

Mnemosyne's architecture was originally captured as a mind-map that drew deployables, pipeline steps,
and third-party systems at the same visual weight. It could not answer the question the build phase
depended on: what has to be stood up as its own deployable, and what does each optional deployable
cost to skip. ADR-012 answered that with a container-level decomposition, settling the naming and
bundling questions the mind-map had left open — `mnemo-curator` as one container holding Inspector
and Resolver, and indexing folded into `mnemo-core`.

That decomposition then went out of date in one respect. The reference reverse proxy was stored under
`deploy/` and injected into a third-party nginx image at runtime. Although Compose ran it separately,
the proxy was not a Mnemosyne component: it had no component directory, image, release artefact, CI
build, or explicit ownership boundary. Edge routing appeared to be deployment plumbing attached to
`mnemo-core` instead of an independently built runtime concern. ADR-016 extracted it as
`mnemo-proxy`, which added a deployed service the decomposition did not list.

This ADR supersedes both and states the decomposition as it now stands, with `mnemo-proxy` in it.

---

## Considered Options

### Option 1: Keep one mind-map covering everything

**Pros:**
- One artefact to maintain

**Cons:**
- Deployables, pipeline steps, and third-party systems drawn at equal weight, so the deploy question
  cannot be read off it
- Colour semantics drift when one diagram carries several conventions

### Option 2: Keep edge routing as mounted deployment configuration

Continue mounting `deploy/reverse-proxy/nginx.conf` into an upstream nginx image rather than treating
the proxy as a deployable.

**Pros:**
- No additional first-party image
- Operators can edit the mounted file directly

**Cons:**
- No versioned proxy artefact or CI image build
- Edge routing reads as plumbing attached to `mnemo-core` rather than an owned runtime boundary

### Option 3: A container-level decomposition on the deployment/ownership axis *(chosen)*

One diagram whose single axis is what gets deployed and who owns it, with control-flow and governance
detail deliberately excluded and nested in component-level diagrams instead. Edge routing is one of
the deployed services on that axis.

**Pros:**
- Answers the deploy question directly: what is required, what is optional, what is lost by skipping
- Gives each artefact one checkable purpose, resolving the colour-semantics drift
- Every deployable — including the proxy — has a component directory, image, CI build, and owner

**Cons:**
- More artefacts to keep in sync as deployables are added or change optionality

---

## Decision

Mnemosyne is decomposed into a container diagram with the following elements.

### Deployed services (we build, we run)

| Container | Required? | What's lost if skipped |
|---|---|---|
| `mnemo-core` | Required | The system does not function without it — it is the governance pipeline (classification, augmentation, dedup, adversarial review, trust model, publish) and also owns indexing. |
| `mnemo-ui` | Optional | Loses the one intake/read surface built for people who aren't already working in Git or an editor plugin. Every other intake route and both publish targets (MkDocs, Confluence) still function without it. |
| `mnemo-proxy` | Optional | Loses first-party edge routing; `mnemo-core` remains independently deployable for headless use, and operators supplying their own ingress are unaffected. |
| `mnemo-curator` | Optional | Loses active drift detection and inline issue resolution. Intake, review, and publish are unaffected — nothing is catching staleness, broken structure, or semantic gaps until a human happens to notice. |
| `mnemo-bot` | Optional | Loses conversational read (semantic search over the Vector DB) and conversational write. All other intake routes and publish targets are unaffected. It is architecturally distinct enough (long-running, conversational, its own technology stack) that a deployer may reasonably choose not to build it at all — a different kind of optionality from `mnemo-ui`/`mnemo-curator`, which are optional in *capability* but not in *technology*. |

### `mnemo-proxy` scope

`mnemo-proxy` routes `/` to `mnemo-ui` and `/api/`, `/mcp/`, and `/health` to `mnemo-core`. It
contains no business, authentication, ingestion, publishing, or governance logic. Source Compose
builds it from its top-level directory; packaged Compose pulls the versioned
`ghcr.io/pabooth/mnemo-proxy` image. Operators may still put a site-specific TLS ingress in front of
it. Both `mnemo-proxy` and `mnemo-ui` are enabled through the optional Compose `ui` profile; an
unprofiled Compose startup runs only `mnemo-core`.

### `mnemo-curator` internal shape

`mnemo-curator` absorbs what were previously drawn as two separate nodes, `Self-Audit`/`Inspector`
and `Issue Resolver`:

- **Inspector** and **Resolver** are components inside the `mnemo-curator` container, not separate
  deployables — the same relationship `mnemo-core`'s internal pipeline stages have to `mnemo-core`.
- Rationale for bundling: Resolver's only trigger was "an issue was just created". Bundling removes
  the need for a separate trigger mechanism (webhook or poll) entirely, since resolution becomes the
  next step in the same scheduled run rather than something a second process has to be notified
  about.
- Even with inline resolution, every finding is still written to the issue tracker before an inline
  fix is attempted — this is the crash-recovery and audit-trail boundary, not just the
  low-confidence path.
- A manual single-issue retry entrypoint (e.g. `--mode=retry --issue=<id>`) exists alongside the
  scheduled full-sweep mode, so a specific stuck issue does not require waiting for or forcing a full
  sweep.
- The container was originally going to be named `mnemo-inspector`, but that name reflects only the
  read/reporting half of the job. `mnemo-curator` covers both inspection and correction; `Inspector`
  and `Resolver` remain the component-level names inside it. The original `Self-Audit` label carried
  the same read-only bias and is retired everywhere it appears.

### Indexing

Indexing is folded into `mnemo-core` rather than being its own container or a CI-pipeline step:

- Not a CI step, because that couples Vector DB freshness to a specific CI vendor's job succeeding
  rather than to Git itself — a poor coupling for something other people will self-host on arbitrary
  Git hosts.
- Not a standalone service, because it is branch-free, stateless embed-and-write logic with no need
  for a persistent process between merges, and it needs the same embedding-model configuration as the
  rest of the system.
- Trigger shape: on-demand primary path, with a low-frequency scheduled reconciliation pass as a
  fallback, not a replacement. The reconciliation pass diffs what is in the repo at `main` against
  what is in the Vector DB, by commit SHA or content hash, and processes only what is missing — it
  must not silently become a second full re-embed job. It also doubles as a monitoring signal: if it
  regularly finds gaps, the on-demand trigger is failing more than expected.
- The specific mechanism for calling it on-demand (webhook, direct call, queue) is an implementation
  decision, not an architectural one, and is deliberately left open.

### First-party clients (we build the code, someone else's runtime hosts it)

- **Obsidian plugin** and **Chrome extension** (browser clipper) are built and maintained by us but
  run inside Obsidian's and Chrome's processes. There is no deployment decision for them the way
  there is for the containers above — a user installs them, nothing is stood up.
- No off-the-shelf equivalent exists for either: a generic clipper or note-taking plugin has no
  notion of Mnemosyne's MCP intake surface, Diataxis classification, or the governance pipeline
  downstream. Bespoke build is the correct call, not a fallback from a failed search.

### External tools (not ours, not our runtime)

- **LLM Desktop Client** and **Git-aware editor** (e.g. Tolaria) are entirely independent of
  Mnemosyne — not our code, not our runtime, no deployment story on our side. They integrate against
  surfaces we expose (MCP, Git) but are otherwise out of scope for the container diagram.

### External / commodity systems

- **Repo (Git)**, **Vector DB**, **MkDocs**, **Confluence** — genuinely third-party systems being
  integrated with, not proprietary logic.

### Actors

- **Human** — the general human actor, fanning out into the specific tools and containers above.
- **Agentic access** — the peer to Human at the actor level. Represents an autonomous agentic loop or
  automation process sitting entirely outside the system as a consumer of it, submitting content
  directly to `mnemo-core` over MCP without going through any specific client tool. The label is
  precise about both the actor and the access path, and avoids "process", which reads as a runtime
  detail rather than an actor type.

---

## Justification

Separating the deployment and ownership axis into its own container-level diagram answers the
question the next build phase depends on, resolves the colour-semantics drift by giving each diagram
one set of conventions, and settles the naming and bundling questions the mind-map left ambiguous.
The cost — more artefacts to keep in sync — is acceptable because each artefact now has a single,
checkable purpose.

Edge routing belongs on that axis as a deployed service rather than beneath it as mounted
configuration. It is a runtime responsibility with its own security, availability, and release
concerns, and a first-party image makes that boundary reviewable and reproducible without coupling it
to the application process. Keeping it optional preserves headless and alternative-ingress
deployments, and keeps `mnemo-core` owning only API, MCP, pipeline, job, and publishing concerns.

---

## Enforcement

- The container diagram is maintained alongside this ADR and updated when deployables are added,
  removed, or change optionality
- Every deployed service has its own top-level component directory, Dockerfile, and CI image build;
  proxy configuration and its Dockerfile live under `mnemo-proxy/`
- Compose assigns the proxy and UI to the optional `ui` profile, and CI validates the complete
  Compose model
- Releases publish a versioned image and standalone archive per deployed service
- Application, authentication, or governance logic must not be added to `mnemo-proxy`
- The `Self-Audit` label is retired from operational guidance, diagrams, docs, and task trackers in favour of `mnemo-curator`; occurrences in this and earlier ADRs stand as historical record of the rename
- Proposals for new deployables, for splitting `mnemo-curator`, for extracting indexing, or for
  moving edge routing into another component must supersede this ADR

---

## Consequences

Positive:
- A deploy checklist: what is required versus optional, and what capability is lost by skipping each
  optional container
- A blast-radius map: which pieces share a release cycle and failure domain, and which are
  independent
- A place for component-level diagrams to nest without competing for space with things that are not
  part of that process — a future `mnemo-core` component diagram no longer has to share a canvas with
  `Repo` or `MkDocs`
- Proxy behaviour is versioned and tested as a distinct artefact, and packaged deployments no longer
  depend on a host-mounted nginx config

Negative / trade-offs:
- Releases contain and publish one additional artefact
- Custom upstream names require a custom image or configuration override
- More artefacts to keep in sync as the system changes

Deliberately not covered:
- Control-flow and governance detail (Diataxis classification, tier routing, the adversarial review
  gate) — that is ADR-021's territory and belongs in a `mnemo-core` component diagram
- The specific triggering mechanism for on-demand indexing — implementation detail, left open
- Failure-mode handling for the indexing reconciliation pass, fail loud versus fail quiet on a bad
  merge — open question, not yet decided
- Whether `mnemo-curator`'s bundled design should be one package with several modes versus something
  more granular — one package for now; revisit if Inspector and Resolver's logic diverges enough to
  justify a split

---

## Related

- [ADR-006: MCP as intake interface only](006-mcp-intake-only.md) — the intake surface this diagram's edges connect into
- [ADR-009: Standalone UI container](009-standalone-ui-container.md) — the independent runtime boundary between UI and core
- [ADR-021: Tiered review with adversarial adjudication and author rebuttal](021-tiered-adversarial-review.md) — the control-flow axis this ADR deliberately excludes

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
