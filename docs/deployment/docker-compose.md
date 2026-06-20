# Deploy with Docker Compose

## Prerequisites

- Docker Engine with Docker Compose
- Credentials for one configured LLM provider
- A GitHub token with permission to create branches, files, and pull requests

## Start Mnemosyne

```bash
cp .env.example .env
```

Set `MNEMO_API_TOKEN`, `GITHUB_TOKEN`, `GITHUB_REPO`, and the credentials for
your selected LLM provider, then run:

```bash
docker compose up --build
```

Open <http://localhost:8888>, open **Settings**, disable mock mode, and enter
the same API token configured in `.env`.

The core API is also available directly at <http://localhost:7777>. Production
deployments should expose only the reverse proxy.

## Observability

Set:

```dotenv
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

Then start the optional profile:

```bash
docker compose --profile observability up --build
```

- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>

Change `GRAFANA_ADMIN_PASSWORD` before exposing Grafana outside a development
machine.

