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

## Webhook intake

| Variable | Purpose |
|---|---|
| `GITHUB_WEBHOOK_SECRET` | HMAC secret configured on the GitHub webhook |
| `GITHUB_WEBHOOK_BRANCH` | Watched branch, default `main` |
| `GITHUB_WEBHOOK_PATH_PREFIX` | Optional path restriction |
| `GITHUB_WEBHOOK_MAX_FILES` | Maximum changed documents per event |

Configure the webhook URL as:

```text
https://mnemosyne.example.com/api/webhooks/github
```

Select the GitHub **push** event and use the same secret in GitHub and
`GITHUB_WEBHOOK_SECRET`.

## URL intake

Remote URL ingestion is disabled by default. Enable only specific hosts:

```dotenv
SOURCE_URL_ALLOWED_HOSTS=docs.example.com,handbook.example.com
```

Redirects are not followed.

## Self-audit

`POST /api/audit/knowledge-base` scans Markdown in the configured repository
for stale review dates, missing owners, duplicate titles, and broken relative
links.

| Variable | Default |
|---|---|
| `AUDIT_STALE_AFTER_DAYS` | `180` |
| `AUDIT_MAX_FILES` | `500` |

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
