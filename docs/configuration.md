# Configuration

## Required settings

| Variable | Purpose |
|---|---|
| `MNEMO_API_TOKEN` | Shared administrator token |
| `GITHUB_TOKEN` | Token used to create branches, files, pull requests, review comments, and eligible Tier 1 merges |
| `GITHUB_REPO` | Target repository in `owner/repository` form |
| `LLM_PROVIDER` | `anthropic`, `openai`, `deepseek`, `xai`, `gemini`, or `ollama` |

Use `MNEMO_API_TOKENS` for named identities:

```dotenv
MNEMO_API_TOKENS=alice:first-secret:submitter,bob:second-secret:admin
```

The shared `MNEMO_API_TOKEN` is treated as an administrator.

## REST API

Content and job routes are versioned under `/api/v1`. `/health` and `/ready`
remain unversioned for infrastructure probes.

Bearer-token REST routes require:

```http
Authorization: Bearer <token>
```

The GitHub webhook route is also under `/api/v1`, but it uses the
`X-Hub-Signature-256` HMAC signature header instead of bearer-token auth.

## Provider settings

| Provider | Variables |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| OpenAI-compatible | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` |
| DeepSeek | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| xAI / Grok | `XAI_API_KEY`, `XAI_BASE_URL`, `XAI_MODEL` |
| Google Gemini | `GEMINI_API_KEY`, `GEMINI_BASE_URL`, `GEMINI_MODEL` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |

## Adversarial review (ADR-011)

| Variable | Default | Purpose |
|---|---|---|
| `ADVERSARIAL_REVIEW_ENABLED` | `false` | Run the dual-model review gate after publishing; when `false`, leave every PR for manual handling and never auto-merge |
| `REVIEWER_ADVOCATE_PROVIDER` | `anthropic` | Provider family instructed to build the acceptance case |
| `REVIEWER_CRITIC_PROVIDER` | `openai` | Provider family instructed to hunt for rejection reasons |

The two values must name different supported provider families. Reviewer slots
reuse the API credentials, endpoint, and model configured for that provider.
Every `/ingest` and `/publish` operation records the structured outcome in a PR
comment. Reviewer disagreement, invalid output, or unavailability escalates to
human review. Tier 2 always requires human approval. Only unanimous Tier 1
acceptance attempts an automatic squash merge.

Setting `ADVERSARIAL_REVIEW_ENABLED=false` skips both reviewer calls, the review
comment, and automatic merge. Publishing still creates a branch and pull request,
and the API returns `null` for the review result. This is an operational fallback;
the PR must then be handled manually.

## Document templates and taxonomy (ADR-018)

Document templates live in the knowledge-base repository, not in
Mnemosyne, in a `templates/` directory beside the Diataxis content
folders (under `DOCS_ROOT` when set):

```text
templates/
├── reference/
│   └── standard.md      # sub-label "standard" of type "reference"
└── how-to/
    └── runbook.md       # sub-label "runbook" of type "how-to"
```

The template set **is** the sub-label taxonomy: the directory names the
Diataxis type, the filename names the sub-label, and the classifier
prompt is assembled from the set at startup. The four Diataxis types
themselves are fixed (ADR-003). A KB with no `templates/` directory has
an empty taxonomy — documents classify to bare types with no sub-label.

Each template is Markdown with a frontmatter `description` — a
single-line value, at most 500 characters. After trimming surrounding
whitespace and quotes, the description is included in the classifier
prompt unchanged — it defines when a document counts as that sub-type,
so write it as deliberately as the body. The body is the section
skeleton used when a submission hints that type and sub-label. A
knowledge base may define at most 100 templates of up to 64 KiB each;
every `(type, sub-label)` pair must be defined exactly once.

mnemo-core fetches the set once at startup using `GITHUB_TOKEN` /
`GITHUB_REPO`. Any fetch failure — bad credentials, wrong repository,
network, or a malformed template file — is fatal: the service logs the
cause and exits, and the container restart policy retries. If
`GITHUB_TOKEN`/`GITHUB_REPO` are not configured at all (a preview-only
deployment that never publishes), there is nothing to fetch: the service
starts with an empty taxonomy and logs a warning. Restart mnemo-core to
pick up merged template changes. Template files are never indexed by
the vector index or scanned by the curator.

Because templates program the classifier, they are Tier 2 governance content.
Guard the directory with protected-branch rules and CODEOWNERS:
changes arrive only by pull request with passing checks and at least
one human approval, a CODEOWNERS rule names who that approver must be,
and rules must prevent the Mnemosyne service account from satisfying or
bypassing that human approval requirement:

```text
/templates/  @your-kb-maintainers
```

Starter templates to copy into a KB live in `examples/templates/` in the
Mnemosyne repository; Mnemosyne itself ships none built in.

## Vector index and embeddings (ADR-014)

`POST /api/v1/index/trigger` and `POST /api/v1/index/reconcile` embed
Markdown content into a pluggable vector index. The reference implementation
is embedded and file-based, so no separate service is required.

| Variable | Default | Purpose |
|---|---|---|
| `VECTOR_STORE` | `sqlite-vec` | Only `sqlite-vec` is currently supported |
| `VECTOR_DB_PATH` | `./data/mnemo-core/vectors.db` (bare-metal) / `/data/vectors.db` (Docker) | Its own file by default (ADR-015), separate from `STATE_DB_PATH`; not set in `mnemosyne.env.example` because Docker Compose hardcodes the container path directly, like `STATE_DB_PATH` |
| `VECTOR_EMBEDDING_DIM` | `1536` | Must match the active embedding model's output size |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `ollama` |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-small` | Uses `OPENAI_API_KEY`/`OPENAI_BASE_URL` |
| `EMBEDDING_OLLAMA_MODEL` | `nomic-embed-text` | Uses `OLLAMA_BASE_URL`; 768-dimensional, so set `VECTOR_EMBEDDING_DIM=768` alongside it |
| `INDEX_MAX_FILES` | `2000` | Cap on files walked during a reconciliation pass |

Set `VECTOR_DB_PATH=""` explicitly to share the same file as `STATE_DB_PATH`
instead of a separate one. Do not set `VECTOR_DB_PATH` in
`$MNEMO_HOME/mnemosyne.env` to a relative path — it would override the
container's hardcoded `/data/vectors.db` with a path relative to the
container's working directory rather than the bind-mounted data directory.

`EMBEDDING_PROVIDER` is independent from `LLM_PROVIDER`: Anthropic and
DeepSeek don't offer an embeddings API, so an OpenAI-compatible or Ollama
embedding model is required regardless of which `LLM_PROVIDER` is used for
classification and augmentation.

Postgres with `pgvector` is the documented scale-out option once a
deployment's corpus outgrows the embedded default; it is not yet implemented.

## Read-path dedup check

`process` and `ingest` can check the vector index for likely-existing
duplicates before returning. Matches never block the pipeline — they're
attached to the response as `duplicate_candidates` and noted in the PR body
for the human reviewer.

| Variable | Default | Purpose |
|---|---|---|
| `DEDUP_ENABLED` | `false` | Off by default — enabling it calls the embedding provider on every `process`/`ingest` |
| `DEDUP_MAX_DISTANCE` | `0.35` | Maximum vector-index distance to still count as a candidate; lower is stricter |
| `DEDUP_TOP_K` | `3` | Maximum candidates returned per document |

`DEDUP_MAX_DISTANCE` is a raw distance from the configured vector store, not
a normalised similarity percentage, and its useful range depends on the
embedding model in use — tune it against real content rather than trusting
the default as-is.

## Operational limits

| Variable | Default |
|---|---|
| `REQUEST_TIMEOUT_SECONDS` | `120` |
| `REQUEST_RATE_LIMIT_PER_MINUTE` | `30` |
| `REQUEST_MAX_CONCURRENCY` | `4` |
| `REQUEST_MAX_BODY_BYTES` | `2000000` |
| `STATE_DB_PATH` | `./data/mnemo-core/state.db` |
| `JOB_MAX_ATTEMPTS` | `2` |
| `JOB_RETRY_BASE_SECONDS` | `1` |

The in-process limiter is suitable for a single core instance. A multi-instance
deployment should enforce distributed limits at its gateway.

## Host bindings

Docker Compose host bindings can be controlled without editing the Compose
files:

| Variable | Default | Purpose |
|---|---|---|
| `MNEMO_UI_BIND_ADDRESS` | `0.0.0.0` | Address for the `mnemo-proxy` interface |
| `MNEMO_CORE_BIND_ADDRESS` | `127.0.0.1` | Address for direct core API access |
| `MNEMO_OBSERVABILITY_BIND_ADDRESS` | `127.0.0.1` | Address for Grafana and Prometheus |
| `MNEMO_PORT_UI` | `8888` | Host port for the main interface |
| `MNEMO_PORT_CORE` | `7777` | Host port for direct core API access |

Use `0.0.0.0` to listen on all host interfaces, `127.0.0.1` for local access
only, or a specific host IP address to listen only on that interface. The main
interface defaults to all host interfaces. Direct core and observability
access default to loopback and should remain private unless placed behind an
authenticated TLS ingress.

## Runtime identity

| Variable | Default | Purpose |
|---|---|---|
| `MNEMO_UID` | `0` | Numeric UID used by the core container |
| `MNEMO_GID` | `0` | Numeric GID used by the core container |

Root is retained as the compatibility default. A dedicated host UID/GID is
strongly recommended for production. The selected identity must have write
access to the directory containing `STATE_DB_PATH`; see the
[Docker deployment guide](./deployment/docker-compose.md#runtime-user).

## Persistence (ADR-015 / ADR-017)

All instance state lives in one directory located by the `MNEMO_HOME`
environment variable — conventionally `~/mnemosyne` on a development
machine, `/srv/mnemosyne` on a Linux server:

```
$MNEMO_HOME/
├── mnemosyne.env          # start-time configuration
└── data/
    ├── mnemo-core/        # state.db (jobs + audit), vectors.db (vector index)
    └── mnemo-curator/     # issues.db (only when CURATOR_ISSUE_TRACKER=sqlite)
```

`MNEMO_HOME` is a deployment setting consumed by Docker Compose alone: it
places the per-component bind mounts (`$MNEMO_HOME/data/<component>` onto
each service's `/data`), and the Compose file hands each container an
explicit container path (`STATE_DB_PATH=/data/state.db` and so on). The
applications never read it. Compose fails with an instructive error if
`MNEMO_HOME` is unset — there is deliberately no fallback into the source
tree.

For bare-metal (non-Docker) runs, the applications' own defaults follow
the same per-component layout relative to the working directory
(`./data/mnemo-core/state.db`, `./data/mnemo-core/vectors.db`,
`./data/mnemo-curator/issues.db`) — run the process with `$MNEMO_HOME` as
its working directory and state lands in the right place. The explicit
`*_DB_PATH` variables override the defaults.

The two components' data directories are never shared, preserving the
failure-domain separation between `mnemo-core` and `mnemo-curator`
established in ADR-012.

All SQLite connections (jobs, vector index, curator's SQLite issue tracker)
run in WAL mode.

Under a non-root `MNEMO_UID`/`MNEMO_GID`, create and `chown` each
component's subdirectory before first run — see
[Docker deployment guide](./deployment/docker-compose.md#runtime-user).
If you are upgrading from a layout that predates ADR-015 (named Docker
volumes, or database files directly in the data root), see
[Migrating from earlier data layouts](./deployment/docker-compose.md#migrating-from-earlier-data-layouts).

### Backup and restore

Do not `cp`, `tar`, or `rsync` a live database file directly. In WAL mode,
recent commits live in a separate `-wal` file that isn't merged into the
main `.db` file until a checkpoint runs; a plain file copy can miss those
commits or capture the `.db` and `-wal` files at inconsistent points in
time, producing a backup that looks fine and fails on restore. Use one of:

**SQLite online backup (no downtime)** — safe to run against a live,
WAL-mode database:

```bash
sqlite3 "$MNEMO_HOME/data/mnemo-core/state.db" ".backup '$BACKUP_DIR/state.db'"
sqlite3 "$MNEMO_HOME/data/mnemo-core/vectors.db" ".backup '$BACKUP_DIR/vectors.db'"
sqlite3 "$MNEMO_HOME/data/mnemo-curator/issues.db" ".backup '$BACKUP_DIR/issues.db'"
```

**Coordinated filesystem snapshot** — an LVM, ZFS/btrfs, or cloud
block-storage snapshot of `$MNEMO_HOME/data` is also safe, provided the
snapshot itself is atomic; unlike `cp`/`tar`/`rsync`, it captures the `.db`,
`-wal`, and `-shm` files at exactly the same instant.

**Quiescence (simplest, requires downtime)** — stop the service, then copy:

```bash
docker compose stop core
cp "$MNEMO_HOME"/data/mnemo-core/*.db* "$BACKUP_DIR/"
docker compose start core
```

The `*.db*` glob deliberately includes any `-wal`/`-shm` siblings: a clean
shutdown checkpoints and removes them, but a container that hit the stop
timeout may leave recent commits in the `-wal` file, and copying only the
`.db` would silently lose them.

Verify every backup immediately, before trusting it:

```bash
sqlite3 "$BACKUP_DIR/state.db" "PRAGMA integrity_check;"
```

Verification also finalises the backup: opening the file makes SQLite
recover and merge any copied `-wal` sibling into the `.db`, so after a
passing `integrity_check` the `.db` alone is the complete backup.

**Restore**: stop the service, replace the live files with verified
backups, delete any stale `-wal`/`-shm` files (they reference offsets in
the old file and are invalid against a restored one), run
`PRAGMA integrity_check` again against the restored file, then restart:

```bash
docker compose stop core
cp "$BACKUP_DIR/state.db" "$MNEMO_HOME/data/mnemo-core/state.db"
rm -f "$MNEMO_HOME"/data/mnemo-core/state.db-wal "$MNEMO_HOME"/data/mnemo-core/state.db-shm
sqlite3 "$MNEMO_HOME/data/mnemo-core/state.db" "PRAGMA integrity_check;"
docker compose start core
```

Do not bring the service back up on a restored file that fails
`integrity_check`.

## Webhook intake

| Variable | Purpose |
|---|---|
| `GITHUB_WEBHOOK_SECRET` | HMAC secret configured on the GitHub webhook |
| `GITHUB_WEBHOOK_BRANCH` | Watched branch, default `main` |
| `GITHUB_WEBHOOK_PATH_PREFIX` | Optional path restriction |
| `GITHUB_WEBHOOK_MAX_FILES` | Maximum changed documents per event |

Configure the webhook URL as:

```text
https://mnemosyne.example.com/api/v1/webhooks/github
```

Select the GitHub **push** event and use the same secret in GitHub and
`GITHUB_WEBHOOK_SECRET`.

## URL intake

Remote URL ingestion is disabled by default. Enable only specific hosts:

```dotenv
SOURCE_URL_ALLOWED_HOSTS=docs.example.com,handbook.example.com
```

Redirects are not followed.

## Curator

`mnemo-curator` is optional. It scans Git-backed Markdown content, records
findings through the configured issue tracker, and can submit safe fixes back
through `mnemo-core`.

| Variable | Default |
|---|---|
| `CURATOR_STALE_AFTER_DAYS` | `180` |
| `CURATOR_MAX_FILES` | `500` |
| `CURATOR_DEFAULT_OWNER` | `unset` |
| `CURATOR_ISSUE_TRACKER` | `github` |
| `CURATOR_ISSUE_LABELS` | `mnemo-curator` |
| `CURATOR_ISSUE_DB_PATH` | `./data/mnemo-curator/issues.db` |
| `CURATOR_SEMANTIC_RESOLUTION_ENABLED` | `false` |

Supported issue trackers:

- `github`: creates issues in `GITHUB_REPO` using `GITHUB_TOKEN`.
- `jira`: creates issues through Jira REST using `JIRA_BASE_URL`,
  `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`, and `JIRA_ISSUE_TYPE`.
- `sqlite`: stores findings locally in `CURATOR_ISSUE_DB_PATH`.

Run a scan with Docker Compose:

```bash
docker compose --profile curator run --rm curator
```

Enable semantic rewrites only when `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and
`OPENAI_MODEL` point to an approved OpenAI-compatible provider.

## OpenTelemetry

Set `OTEL_EXPORTER_OTLP_ENDPOINT` to enable traces and metrics. Structured JSON
logs are emitted independently. `LOG_LEVEL` defaults to `INFO`.

## Provider evaluation

After changing a model or prompt, run:

```bash
mnemo-evaluate --minimum-accuracy 0.75
```

The command checks valid structured output and classification accuracy against
a small representative Diátaxis set. It makes billable calls for hosted
providers.
