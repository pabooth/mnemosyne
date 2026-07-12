# Configuration

## Required settings

| Variable | Purpose |
|---|---|
| `MNEMO_API_TOKEN` | Shared administrator token |
| `GITHUB_TOKEN` | Token used to create branches, files, and pull requests |
| `GITHUB_REPO` | Target repository in `owner/repository` form |
| `LLM_PROVIDER` | `anthropic`, `openai`, `deepseek`, or `ollama` |

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
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |

## Vector index and embeddings (ADR-014)

`POST /api/v1/index/trigger` and `POST /api/v1/index/reconcile` embed
Markdown content into a pluggable vector index. The reference implementation
is embedded and file-based, so no separate service is required.

| Variable | Default | Purpose |
|---|---|---|
| `VECTOR_STORE` | `sqlite-vec` | Only `sqlite-vec` is currently supported |
| `VECTOR_DB_PATH` | `./data/vectors.db` (bare-metal) / `/data/vectors.db` (Docker) | Its own file by default (ADR-015), separate from `STATE_DB_PATH`; not set in `.env.example` because Docker Compose hardcodes the container path directly, like `STATE_DB_PATH` |
| `VECTOR_EMBEDDING_DIM` | `1536` | Must match the active embedding model's output size |
| `EMBEDDING_PROVIDER` | `openai` | `openai` or `ollama` |
| `EMBEDDING_OPENAI_MODEL` | `text-embedding-3-small` | Uses `OPENAI_API_KEY`/`OPENAI_BASE_URL` |
| `EMBEDDING_OLLAMA_MODEL` | `nomic-embed-text` | Uses `OLLAMA_BASE_URL`; 768-dimensional, so set `VECTOR_EMBEDDING_DIM=768` alongside it |
| `INDEX_MAX_FILES` | `2000` | Cap on files walked during a reconciliation pass |

Set `VECTOR_DB_PATH=""` explicitly to share the same file as `STATE_DB_PATH`
instead of a separate one. Do not set `VECTOR_DB_PATH` in a Docker Compose
`.env` file to a relative path — it would override the container's hardcoded
`/data/vectors.db` with a path relative to the container's working directory
rather than the bind-mounted data directory.

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
| `STATE_DB_PATH` | `./data/mnemosyne.db` |
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

## Persistence (ADR-015)

Data is bind-mounted to the host, not stored in anonymous Docker volumes.
Each deployable gets its own subdirectory of one configurable parent:

| Variable | Default (Compose) | Default (packaged) | Purpose |
|---|---|---|---|
| `MNEMO_DATA_DIR` | `./data` | `/var/lib/mnemosyne/data` | Parent directory; each service writes to `$MNEMO_DATA_DIR/<component>` |

`mnemo-core` writes to `$MNEMO_DATA_DIR/mnemo-core` (`mnemosyne.db`,
`vectors.db`); `mnemo-curator` writes to `$MNEMO_DATA_DIR/mnemo-curator`
(`mnemo-curator-issues.db`, only when `CURATOR_ISSUE_TRACKER=sqlite`). The
two are never shared, preserving the failure-domain separation between
`mnemo-core` and `mnemo-curator` established in ADR-012.

All SQLite connections (jobs, vector index, curator's SQLite issue tracker)
run in WAL mode.

Under a non-root `MNEMO_UID`/`MNEMO_GID`, create and `chown` each
component's subdirectory before first run — see
[Docker deployment guide](./deployment/docker-compose.md#runtime-user).

### Backup and restore

Do not `cp`, `tar`, or `rsync` a live database file directly. In WAL mode,
recent commits live in a separate `-wal` file that isn't merged into the
main `.db` file until a checkpoint runs; a plain file copy can miss those
commits or capture the `.db` and `-wal` files at inconsistent points in
time, producing a backup that looks fine and fails on restore. Use one of:

**SQLite online backup (no downtime)** — safe to run against a live,
WAL-mode database:

```bash
sqlite3 "$MNEMO_DATA_DIR/mnemo-core/mnemosyne.db" ".backup '$BACKUP_DIR/mnemosyne.db'"
sqlite3 "$MNEMO_DATA_DIR/mnemo-core/vectors.db" ".backup '$BACKUP_DIR/vectors.db'"
sqlite3 "$MNEMO_DATA_DIR/mnemo-curator/mnemo-curator-issues.db" ".backup '$BACKUP_DIR/mnemo-curator-issues.db'"
```

**Coordinated filesystem snapshot** — an LVM, ZFS/btrfs, or cloud
block-storage snapshot of `$MNEMO_DATA_DIR` is also safe, provided the
snapshot itself is atomic; unlike `cp`/`tar`/`rsync`, it captures the `.db`,
`-wal`, and `-shm` files at exactly the same instant.

**Quiescence (simplest, requires downtime)** — stop the service, then copy:

```bash
docker compose stop core
cp "$MNEMO_DATA_DIR"/mnemo-core/*.db "$BACKUP_DIR/"
docker compose start core
```

Verify every backup immediately, before trusting it:

```bash
sqlite3 "$BACKUP_DIR/mnemosyne.db" "PRAGMA integrity_check;"
```

**Restore**: stop the service, replace the live files with verified
backups, delete any stale `-wal`/`-shm` files (they reference offsets in
the old file and are invalid against a restored one), run
`PRAGMA integrity_check` again against the restored file, then restart:

```bash
docker compose stop core
cp "$BACKUP_DIR/mnemosyne.db" "$MNEMO_DATA_DIR/mnemo-core/mnemosyne.db"
rm -f "$MNEMO_DATA_DIR"/mnemo-core/mnemosyne.db-wal "$MNEMO_DATA_DIR"/mnemo-core/mnemosyne.db-shm
sqlite3 "$MNEMO_DATA_DIR/mnemo-core/mnemosyne.db" "PRAGMA integrity_check;"
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
| `CURATOR_ISSUE_DB_PATH` | `./data/mnemo-curator-issues.db` |
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
