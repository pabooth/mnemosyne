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
| `MNEMO_UI_BIND_ADDRESS` | `0.0.0.0` | Address for the main reverse-proxy interface |
| `MNEMO_CORE_BIND_ADDRESS` | `127.0.0.1` | Address for direct core API access |
| `MNEMO_OBSERVABILITY_BIND_ADDRESS` | `127.0.0.1` | Address for Grafana and Prometheus |
| `MNEMO_PORT_UI` | `8888` | Host port for the main interface |
| `MNEMO_PORT_CORE` | `7777` | Host port for direct core API access |

Use `0.0.0.0` to listen on all host interfaces, `127.0.0.1` for local access
only, or a specific host IP address to listen only on that interface. The main
interface defaults to all host interfaces. Direct core and observability
access default to loopback and should remain private unless placed behind an
authenticated TLS reverse proxy.

## Runtime identity

| Variable | Default | Purpose |
|---|---|---|
| `MNEMO_UID` | `0` | Numeric UID used by the core container |
| `MNEMO_GID` | `0` | Numeric GID used by the core container |

Root is retained as the compatibility default. A dedicated host UID/GID is
strongly recommended for production. The selected identity must have write
access to the directory containing `STATE_DB_PATH`; see the
[Docker deployment guide](./deployment/docker-compose.md#runtime-user).

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
