# ADR-017: Instance directory — deployment state under `MNEMO_HOME`, separate from the source tree

> **Status:** `Accepted`
> **Date:** 2026-07-13
> **Review date:** 2027-07-13

---

## Identity

| Field | Value |
|---|---|
| **ID** | ADR-017 |
| **Title** | Instance directory — deployment state under `MNEMO_HOME`, separate from the source tree |
| **Status** | Accepted |
| **Date** | 2026-07-13 |
| **Review date** | 2027-07-13 |
| **Supersedes** | — |
| **Superseded by** | — |
| **Amends** | ADR-015 |
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

ADR-015 moved persistent data out of anonymous Docker volumes into bind-mounted, per-component directories, defaulting to `./data` inside the repository checkout. Start-time configuration lives in `.env`, also at the checkout root. Both are gitignored, but both make the source tree double as the deployment instance: a fresh clone, a second worktree, or `git clean -dx` silently loses API keys and databases — including a vector index that costs real embedding-provider spend to rebuild. This affects development as much as production, because checkouts are precisely the thing developers destroy and recreate.

Two further irritants surfaced while reviewing the persistence story:

- Configuration and data are both instance state with the same lifecycle ("as long as this installation exists"), yet they had no shared home, and the documented production story (the `.deb`/`.rpm` compose wrapper, since removed) scattered them across `/etc/mnemosyne`, `/var/lib/mnemosyne`, and — through an interpolation bug — `/usr/share/mnemosyne`.
- The three SQLite files followed three naming conventions: `mnemosyne.db` (product name), `vectors.db` (bare function), `mnemo-curator-issues.db` (component-prefixed function), with the prefix made redundant by ADR-015's per-component directories.

A decision is needed on where instance state lives, how the deployment finds it, and what the databases are called.

---

## Considered Options

### Storage location for instance state

#### Option 1: Status quo — config and data inside the checkout

**Pros:**
- Zero setup; Docker Compose auto-discovers `.env` in the project directory

**Cons:**
- The checkout stops being disposable; checkout-lifecycle events (re-clone, clean, worktrees) destroy secrets and paid-for data
- Conflates source tree (build input) with instance (runtime state)

#### Option 2: FHS split — config in `/etc/mnemosyne`, data in `/var/lib/mnemosyne`

**Pros:**
- Traditional and correct on a Linux server

**Cons:**
- Two locations to know about, back up, and migrate
- Hostile on macOS development machines: the root filesystem is read-only (requires `synthetic.conf` firmlinks and a reboot), the paths sit outside Docker Desktop's default file-sharing allowlist, and both directories are root-owned

#### Option 3: One instance directory, located by `MNEMO_HOME` *(chosen)*

A single directory holds everything that makes an installation that installation — `mnemosyne.env` plus `data/<component>/`. The `MNEMO_HOME` environment variable locates it; the conventional value differs by context (`~/mnemosyne` on a development Mac, `/srv/mnemosyne` on a Linux server) but every instruction and tool speaks only in terms of the variable.

**Pros:**
- The instance is one movable, backupable unit with a lifecycle independent of any checkout
- Identical instructions on macOS and Linux after one `export` line; no OS-specific fights
- Preserves the deployment/application config boundary: `MNEMO_HOME` is consumed by Docker Compose only, never by application code

**Cons:**
- One-time setup per machine (create the directory, export the variable) instead of zero-setup auto-discovery

### Database file naming

#### Option 1: Keep existing names

**Cons:**
- Three files, three conventions; `mnemosyne.db` says nothing about its contents; `mnemo-curator-issues.db` repeats what its directory already states

#### Option 2: Function-named, matching the variable that points at each *(chosen)*

**Pros:**
- One convention — `<component>/<function>.db` — where each filename echoes its configuration variable (`STATE_DB_PATH` → `state.db`, `VECTOR_DB_PATH` → `vectors.db`, `CURATOR_ISSUE_DB_PATH` → `issues.db`)

**Cons:**
- One more rename inside a migration operators already have to perform for ADR-015's layout change

---

## Decision

1. All persistent instance state lives in one directory located by the `MNEMO_HOME` environment variable: `$MNEMO_HOME/mnemosyne.env` (start-time configuration) and `$MNEMO_HOME/data/<component>/` (ADR-015's per-component data directories, re-parented). Conventional locations: `~/mnemosyne` for development, `/srv/mnemosyne` for Linux servers.
2. Docker Compose requires `MNEMO_HOME` and fails loudly without it (`${MNEMO_HOME:?…}` interpolation). The `./data` fallback and the `MNEMO_DATA_DIR` variable are removed; data on a different disk is handled by symlinking `$MNEMO_HOME/data`.
3. The configuration file is a visible `mnemosyne.env`, passed to Compose explicitly (`COMPOSE_ENV_FILES="$MNEMO_HOME/mnemosyne.env"` exported once, or `--env-file` per invocation). Auto-discovery of a checkout-root `.env` is no longer part of the deployment contract.
4. Databases are named by function within their component directory: `mnemo-core/state.db` (durable jobs and audit), `mnemo-core/vectors.db` (vector index), `mnemo-curator/issues.db` (curator findings).
5. Application code never reads `MNEMO_HOME` — it is deployment configuration. Bare-metal runs use the applications' relative defaults (`./data/<component>/<function>.db`) resolved against the working directory, so running a process with `$MNEMO_HOME` as its working directory lands state in the right place; the explicit `*_DB_PATH` variables override as before.

---

## Justification

The instance directory answers the actual failure mode: state with an installation-long lifecycle was keyed to a directory with a disposable lifecycle. Collapsing config and data into one home makes backup, migration, and reasoning about an installation a single-directory affair, and standardising the *variable* rather than the *path* buys identical operator instructions on macOS and Linux without fighting either OS (macOS's read-only root and Docker Desktop's file-sharing allowlist rule out literal `/srv` parity).

Failing loudly when `MNEMO_HOME` is unset is deliberate: the previous `./data` default was exactly the mechanism by which state silently accumulated in checkouts. An explicit error at first run costs a minute; silent state in a disposable directory costs a vector index.

Dropping `MNEMO_DATA_DIR` removes a second knob that overlapped the first — it was Compose-only interpolation dressed up as application configuration, and the removed packaged deployment already demonstrated how that ambiguity produces misplaced data.

The renames make the naming self-consistent at the cheapest possible moment: inside a migration that ADR-015 already obliges existing deployments to perform.

---

## Enforcement

- Compose files must reference instance state exclusively through `${MNEMO_HOME:?…}` with a helpful error message; no compose path may default to a checkout-relative data or config location
- New persistent state goes under `$MNEMO_HOME/data/<component>/` with a function-derived filename matching its configuration variable
- Application code must not read `MNEMO_HOME`; applications receive explicit paths (containers) or use relative defaults (bare-metal)
- Documentation and quick starts must express locations in terms of `$MNEMO_HOME`, never a literal per-OS path, beyond stating the two conventional values
- Any proposal to reintroduce checkout-resident state or a parallel data-location variable should reference and supersede this ADR

---

## Consequences

Positive:
- Checkouts are disposable again; instance state survives re-clones, worktrees, and `git clean`
- One directory to back up, move, or inspect per installation, on either OS
- Misconfiguration fails with an instructive error instead of scattering state
- Database names state their function and match the variables that configure them

Negative / trade-offs:
- One-time setup per machine (`mkdir`, `cp`, one `export` in the shell profile) replaces zero-setup auto-discovery
- Existing deployments must move `.env` and `data/` into an instance directory and rename three database files — folded into the ADR-015 migration documentation
- Plain `docker compose config` (and CI invocations of it) must provide `MNEMO_HOME`

---

## Related

- [ADR-012: Container-level decomposition of Mnemosyne](012-container-decomposition.md) — the per-component isolation the instance directory preserves
- [ADR-015: Persistence layout](015-persistence-layout.md) — amended by this ADR: per-component directories, separate files, and WAL mode stand; the storage location (`./data` default, `MNEMO_DATA_DIR`) and file names are replaced

---

*This ADR follows the Mnemosyne Project ADR standard.*
*Template version: 1.0 — June 2026*
