# ADR-014: Pluggable vector-index layer with an embedded reference implementation

> **Status:** `Accepted`
> **Date:** 2026-07-09
> **Review date:** 2027-07-09

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-014 |
| **Title** | Pluggable vector-index layer with an embedded reference implementation |
| **Status** | Accepted |
| **Date** | 2026-07-09 |
| **Review date** | 2027-07-09 |
| **Supersedes** | — |
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

ADR-012 folded indexing into `mnemo-core` as stateless embed-and-write logic, on-demand with a low-frequency reconciliation fallback, and drew the Vector DB itself as an external/commodity system alongside Git, MkDocs, and Confluence. ADR-013 stubbed the corresponding routes — `POST /api/v1/index/trigger` and `POST /api/v1/index/reconcile` — both of which currently queue durable jobs that fail immediately with `NotImplementedError`.

No storage technology has been chosen yet, and none of the capabilities that depend on it exist: the read-path dedup check ahead of classification, and `mnemo-bot`'s conversational semantic read, which cannot function at all without a vector index. A decision is needed on both the deployment shape (embedded vs. standalone server) and the specific technology, before the index/trigger and index/reconcile stubs can be implemented.

---

## Considered Options

### Deployment shape

#### Option 1: Standalone vector DB server (Qdrant, Weaviate, Milvus, or Postgres/pgvector)

**Pros:**
- Mature at scale — proper ANN indexing (HNSW, IVF-PQ), hybrid search, horizontal scale-out
- Matches ADR-012's diagram, which already draws the Vector DB as its own external box

**Cons:**
- A new required-or-optional service every self-hoster must stand up and operate
- Cuts against the project's low-ops bias demonstrated elsewhere: indexing was folded into `mnemo-core` specifically to avoid a new deployable, and `mnemo-curator` stays behind an optional Compose profile
- Disproportionate operational weight for the corpus sizes a documentation KB is expected to reach

#### Option 2: Embedded, file-based vector store *(chosen)*

**Pros:**
- No new service to deploy or operate
- Consistent with the existing SQLite-backed durable job store (`mnemo_core/jobs.py`)
- Fits the `.deb`/`.rpm` bare-metal distribution path and Docker Compose without a new profile
- Corpus size for an ingested documentation KB is not expected to approach the range where embedded engines struggle

**Cons:**
- Lower ceiling on recall/index sophistication and horizontal scale than a dedicated server
- A migration path will be needed if corpus size or query load ever exceeds it

### Embedded engine

#### Option A: `sqlite-vec` *(chosen)*

**Pros:**
- Loads as a SQLite extension into the same database file/connection `mnemo-core` already uses for durable jobs — no second storage subsystem
- Pure C, no additional runtime dependency
- MIT-licensed

**Cons:**
- Younger project than the alternatives
- Brute-force/partition-based KNN rather than a mature ANN index; less proven at larger scales

#### Option B: LanceDB

**Pros:**
- Purpose-built vector-native storage with more mature ANN indexing (IVF-PQ) and built-in versioning

**Cons:**
- Introduces a second embedded storage engine and file format alongside SQLite, for both us and self-hosters to reason about, when SQLite already covers embedded file-based storage

---

## Decision

1. Vector storage is a pluggable layer, following the same pattern as ADR-004 (LLM) and ADR-007 (KB layer): a defined contract — upsert embeddings with metadata, similarity search, delete-by-id, and reconcile-by-content-hash — with a reference implementation.
2. The reference implementation is embedded and file-based: `sqlite-vec`, sharing the SQLite file/connection already used for durable job storage in `mnemo-core`.
3. Postgres with `pgvector` is documented as the supported scale-out option for deployments that outgrow the embedded default. It is not built as part of this ADR.
4. This ADR does not decide the on-demand indexing trigger mechanism (left open by ADR-012) or the embedding model/provider (governed by ADR-004's pluggable LLM layer).

---

## Justification

This follows the same pluggable-interface-plus-reference-implementation shape already established for the LLM layer (ADR-004) and the KB layer (ADR-007), so it is a familiar, low-risk architectural pattern rather than a new one.

Self-hosting simplicity is a load-bearing project value, already demonstrated by folding indexing into `mnemo-core` instead of standing up a separate service (ADR-012) and by keeping `mnemo-curator` behind an optional Compose profile. A standalone vector DB server as the default would undercut that consistency. The corpus a documentation ingestion pipeline produces is not expected to approach the scale where embedded engines become the bottleneck, which is the specific judgement this decision rests on — if that assumption changes, Postgres/pgvector is the documented escape hatch rather than something to build speculatively now.

Reusing the SQLite file already used for jobs, via `sqlite-vec`, avoids introducing a second embedded storage subsystem. LanceDB is a reasonable alternative on technical merits alone, but it would add a second file format and engine for no benefit at the scale this reference implementation targets.

---

## Enforcement

- Vector index access goes through the pluggable contract module, not direct `sqlite-vec` calls scattered through pipeline code — mirrors the `llm/factory.py` pattern
- The storage backend is configured via environment variable (default `sqlite-vec`), not hardcoded, consistent with ADR-004 and ADR-007's enforcement of configuration over hardcoding
- The `index/trigger` and `index/reconcile` stub routes (ADR-013) are implemented against this contract when indexing logic lands
- Any proposal to build the Postgres/`pgvector` scale-out option, or to change the reference implementation, should reference and supersede this ADR

---

## Consequences

Positive:
- `mnemo-bot` and the read-path dedup check become buildable
- No new deployable or service is required to run the reference indexing setup, consistent with the project's existing low-ops posture
- Contributors already familiar with the LLM/KB pluggability pattern can onboard onto this one quickly

Negative / trade-offs:
- `sqlite-vec` is younger and less proven at scale than `pgvector` or a dedicated vector DB
- The migration path to Postgres/`pgvector`, when eventually needed, is not designed yet and will require a data migration story
- Brute-force/partition KNN means recall or query latency may degrade before a mature ANN index would hit the same limits

---

## Related

- [ADR-004: Pluggable LLM layer](004-llm-abstraction.md)
- [ADR-007: Implement a pluggable KB layer with MkDocs Material as the reference implementation](007-kb-layer-pluggability.md)
- [ADR-012: Container-level decomposition of Mnemosyne](012-container-decomposition.md) — draws the Vector DB as an external system and folds indexing into `mnemo-core`
- [ADR-013: API Contract & Versioning Strategy](013-api-contract-versioning.md) — the `index/trigger`/`index/reconcile` stubs this ADR's contract will be implemented behind

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
