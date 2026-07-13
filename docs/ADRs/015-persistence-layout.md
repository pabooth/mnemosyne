# ADR-015: Persistence layout — bind-mounted, component-named data directories with WAL-mode SQLite

> **Status:** `Accepted`
> **Date:** 2026-07-11
> **Review date:** 2027-07-11

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-015 |
| **Title** | Persistence layout — bind-mounted, component-named data directories with WAL-mode SQLite |
| **Status** | Accepted |
| **Date** | 2026-07-11 |
| **Review date** | 2027-07-11 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Amended by** | [ADR-017](017-instance-directory.md) — storage location and database file names; per-component directories, file separation, and WAL mode stand |

---

## Ownership

| Field | Value |
|---|---|
| **Author / Decision Owner** | Paul Booth |
| **Contributors** | — |
| **Consulted** | — |

---

## Context

ADR-012 made `mnemo-core` and `mnemo-curator` separate deployables with separate failure domains. Both have always persisted state to SQLite behind anonymous, Docker-managed named volumes (`mnemo-data`, `mnemo-curator-data`) — no explicit host path, no documented backup or restore procedure, and on Docker Desktop (macOS/Windows) not even directly visible on the host filesystem.

That was an acceptable gap while the data behind it was disposable: durable job records (`mnemo_core/jobs.py`) cost nothing to lose beyond audit history, since jobs can be safely resubmitted. Two things have since changed that:

- ADR-014 added a vector index that, by default, shares the same SQLite file as durable job storage. That file now sees two different write patterns — frequent small job-status updates, and bursty embedding upserts during indexing — contending for the same file lock under SQLite's default rollback-journal mode.
- The vector index and, for `CURATOR_ISSUE_TRACKER=sqlite` deployments, `mnemo-curator`'s issue tracker both hold state that is expensive or impossible to reconstruct: embeddings represent real embedding-provider API spend, and the SQLite issue tracker is the only record of every finding `mnemo-curator` has ever caught.

A decision is needed on where this state actually lives on disk, whether mnemo-core's two SQLite-backed concerns should keep sharing one file, and whether SQLite's concurrency mode is still appropriate now that the data behind it matters more than it used to.

---

## Considered Options

### Storage location

#### Option 1: Keep anonymous named Docker volumes

**Pros:**
- Already in place; portable across hosts without host-path permission setup

**Cons:**
- Opaque — no discoverable host path, no documented backup/restore story
- Not directly visible on the host filesystem under Docker Desktop (macOS/Windows)

#### Option 2: Bind-mount to a configurable parent directory, one subdirectory per component *(chosen)*

**Pros:**
- Visible host path, backed up with a WAL-safe procedure (SQLite's online-backup API or a coordinated filesystem snapshot) instead of an opaque volume with no story at all — see `docs/configuration.md`'s Persistence section for the actual steps
- Consistent with `/etc/mnemosyne/` already existing for config (ADR-013's packaged deployment)
- Per-component subdirectory preserves ADR-012's failure-domain separation — no directory or volume is shared between `mnemo-core` and `mnemo-curator`

**Cons:**
- Requires the host directory to exist with correct ownership before first run under a non-root `MNEMO_UID`/`MNEMO_GID` — already true and already documented for the prior named-volume setup, not a new requirement

### File separation within mnemo-core

#### Option 1: Keep the vector index sharing `state_db_path` (ADR-014 default)

**Pros:**
- One file, simplest mental model

**Cons:**
- Job-status writes and embedding upserts contend for the same SQLite file lock under default rollback-journal mode

#### Option 2: Separate file per concern, same directory *(chosen)*

**Pros:**
- No lock contention between job churn and embedding writes
- Stays inside the same directory/failure domain — doesn't reopen ADR-012's deployable boundary, since both files belong to `mnemo-core` alone

**Cons:**
- Two files instead of one — mitigated by both living in the same subdirectory and therefore the same backup

### Concurrency mode

#### Option 1: Default SQLite rollback journal (status quo)

**Cons:**
- Writers block readers and other writers for the duration of a transaction

#### Option 2: WAL (write-ahead log) mode *(chosen)*

**Pros:**
- Readers and writers don't block each other in the common case — a better fit now that `mnemo-core`'s data sees at least two independent write patterns and `mnemo-curator`'s issue tracker sees concurrent scan/resolve writes

**Cons:**
- Requires the database file's directory to be on a filesystem that supports WAL (not all network filesystems do) — worth a documentation note, not a reason to avoid it, since none of this project's deployment paths target network filesystems for `/data`

---

## Decision

1. Data lives in bind-mounted host directories, not anonymous named Docker volumes. The parent directory is configurable via `MNEMO_DATA_DIR` — default `./data` for the Compose dev path, `/var/lib/mnemosyne/data` for the packaged (`.deb`/`.rpm`) deployment.
2. Each deployable gets its own subdirectory named after the component: `$MNEMO_DATA_DIR/mnemo-core`, `$MNEMO_DATA_DIR/mnemo-curator`. No directory or volume is shared between `mnemo-core` and `mnemo-curator`.
3. Within `mnemo-core`'s own subdirectory, durable jobs (`mnemosyne.db`) and the vector index (`vectors.db`) are separate files by default. `VECTOR_DB_PATH=""` remains a supported explicit opt-in for sharing one file.
4. All SQLite connections — jobs, vector index, and `mnemo-curator`'s SQLite issue tracker — open in WAL mode (`PRAGMA journal_mode=WAL`).

---

## Justification

The bind-mount decision answers the actual gap directly: there was no documented backup/restore story, and anonymous named volumes are invisible from the host under Docker Desktop. Component-named subdirectories under one parent give operators a single location to know about and back up, without recoupling the failure-domain separation ADR-012 established — each service still only ever sees its own subtree.

The file split matters because the risk profile of this data changed after ADR-014. Durable job records were always disposable. The vector index is not — losing it means re-spending real embedding-provider API budget to rebuild it (the `index_reconcile` job is a recovery path, not a substitute for not losing the data in the first place). Sharing one file was a reasonable simplification when ADR-014 was written and the indexer didn't exist yet; now that it does, the lock contention between job churn and embedding writes is real, and separating them costs nothing beyond one extra filename in the same directory.

WAL mode is the standard answer to concurrent SQLite access and costs nothing to enable across all three stores.

---

## Enforcement

- New SQLite-backed state lives under its component's subdirectory of `MNEMO_DATA_DIR`; it must never be shared with another deployable's subdirectory
- New SQLite connections must enable WAL mode on open, consistent with `mnemo_core/jobs.py`, `mnemo_core/vector/sqlite_vec.py`, and `mnemo_curator/issue_trackers.py`
- Non-root `MNEMO_UID`/`MNEMO_GID` deployments must pre-create and `chown` each component's data subdirectory before first run — documented in `docs/deployment/docker-compose.md`
- Backups must use the documented WAL-safe procedure (SQLite online backup or a coordinated filesystem snapshot) in `docs/configuration.md`, never a plain file copy of a live database — and every restore must pass `PRAGMA integrity_check` before the service is brought back up
- Any proposal to share storage between `mnemo-core` and `mnemo-curator`, or to reintroduce anonymous named volumes, should reference and supersede this ADR

---

## Consequences

Positive:
- Operators have one documented location (`MNEMO_DATA_DIR`) to know about, inspect, and back up
- `mnemo-core`'s job churn and embedding writes no longer contend for the same file lock
- WAL mode improves concurrent read/write behaviour across all three SQLite-backed stores
- ADR-012's failure-domain separation between `mnemo-core` and `mnemo-curator` is preserved, not reopened

Negative / trade-offs:
- Bind mounts require the host directory to exist with correct ownership before first run under non-root UID/GID — an existing requirement made explicit rather than incidental to named-volume behaviour
- Two files instead of one inside `mnemo-core`'s data directory
- No automated backup mechanism is shipped by this ADR — it documents the manual, WAL-safe procedure (`docs/configuration.md`) and requires restore verification, but scheduling and running it is left to the operator; automation remains a follow-up if the project wants it

---

## Related

- [ADR-012: Container-level decomposition of Mnemosyne](012-container-decomposition.md) — the failure-domain separation this ADR preserves
- [ADR-014: Pluggable vector-index layer with an embedded reference implementation](014-vector-index-pluggability.md) — the default file-sharing behaviour this ADR changes

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
