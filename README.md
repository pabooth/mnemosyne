![Mnemosyne](./header.png)

[![Tests](https://img.shields.io/github/actions/workflow/status/pabooth/mnemosyne/tests.yml)](https://github.com/pabooth/mnemosyne/actions/workflows/tests.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/github/actions/workflow/status/pabooth/mnemosyne/ci.yml?branch=main)
![Version](https://img.shields.io/github/v/release/pabooth/mnemosyne)

Mnemosyne is an open-source, AI-assisted document ingestion engine. It
classifies source material using the [Diátaxis framework](https://diataxis.fr),
improves its structure and metadata, and opens a pull request for human review.
It never merges generated content.

The project contains:

- `mnemo-core`: REST API, MCP server, processing pipeline, durable jobs, audit
  history, GitHub publishing, webhook intake, and knowledge-base self-audit.
- `mnemo-ui`: optional static browser interface for previewing, editing, and
  submitting documents.

## Quick start

Requirements:

- Docker with Docker Compose
- credentials for Anthropic, OpenAI-compatible APIs, DeepSeek, or Ollama
- a GitHub token with permission to create branches, files, and pull requests

```bash
cp .env.example .env
```

Set `MNEMO_API_TOKEN`, `GITHUB_TOKEN`, `GITHUB_REPO`, and your LLM credentials,
then run:

```bash
docker compose up --build
```

Open <http://localhost:8888>. Enter `MNEMO_API_TOKEN` under **Settings**.
The token is kept in browser session storage rather than persistent local
storage.

For the optional telemetry stack:

```bash
docker compose --profile observability up --build
```

See [the Docker deployment guide](./docs/deployment/docker-compose.md).
Tagged releases also publish `.deb` and `.rpm` deployment packages. After
installation, configure `/etc/mnemosyne/mnemosyne.env` and run
`mnemosyne up -d`.

## Intake interfaces

| Interface | Purpose |
|---|---|
| `POST /api/process` | Synchronous preview |
| `POST /api/ingest` | Synchronous processing and pull request |
| `POST /api/publish` | Publish an edited, reviewed preview without rerunning the LLM |
| `POST /api/jobs` | Durable asynchronous process or ingest job |
| `POST /api/jobs/batch` | Batch submission |
| `POST /api/sources/file` | Markdown or text upload |
| `POST /api/sources/url` | Allow-listed URL intake |
| `POST /api/sources/github` | File intake from the configured GitHub repository |
| `POST /api/webhooks/github` | Signed GitHub push webhook |
| `/mcp/sse` | MCP intake server |

All `/api` intake routes require `Authorization: Bearer <token>`. GitHub
webhooks use `X-Hub-Signature-256` instead.

## Providers

Set `LLM_PROVIDER` to one of:

- `anthropic`
- `openai`
- `deepseek`
- `ollama`

OpenAI-compatible endpoints can be selected using `OPENAI_BASE_URL`. Provider
and operational settings are documented in
[configuration.md](./docs/configuration.md).

## Governance and safety

- Generated content can only be published to a feature branch and pull request.
- Preview output can be edited and then submitted verbatim through
  `/api/publish`.
- Inputs and generated outputs are validated and size-limited.
- Requests have configurable rate, concurrency, and timeout limits.
- Named API tokens support `submitter` and `admin` roles.
- Jobs and mutating API operations are recorded in SQLite.
- URL ingestion is disabled until an explicit hostname allow-list is set.

Repository branch protection must still require human approval and prevent the
Mnemosyne service account from merging.

## Development

```bash
cd mnemo-core
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest

cd ../mnemo-ui
npm install
npm test
npm run build
```

See [CONTRIBUTING.md](./CONTRIBUTING.md), [SECURITY.md](./SECURITY.md), and
[ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## License

MIT. See [LICENSE](./LICENSE).
