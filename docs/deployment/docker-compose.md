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
docker compose --profile ui up --build
```

This enables the optional `ui` profile, which starts `mnemo-ui` and
`mnemo-proxy` alongside the required core service. For a headless deployment,
omit the profile:

```bash
docker compose up --build
```

That command starts only `mnemo-core`. The `curator` and `observability`
services also remain disabled unless their profiles are explicitly enabled.

Open <http://localhost:8888>, open **Settings**, disable mock mode, and enter
the same API token configured in `.env`.

The core API is also available directly at <http://localhost:7777>. Its host
port is bound to `127.0.0.1`, so it is not reachable from other machines.
Production deployments should expose only `mnemo-proxy` (or an equivalent
site-managed ingress).

Host bindings can be configured in `.env`:

```dotenv
MNEMO_UI_BIND_ADDRESS=0.0.0.0
MNEMO_CORE_BIND_ADDRESS=127.0.0.1
MNEMO_OBSERVABILITY_BIND_ADDRESS=127.0.0.1
```

`MNEMO_UI_BIND_ADDRESS=0.0.0.0` exposes the `mnemo-proxy` interface on
all host network interfaces. Set it to a specific host address to bind only
that interface, or `127.0.0.1` for local access only. Keep the core and
observability bindings on loopback unless they are protected by an
authenticated TLS ingress.

## Runtime user

The core container uses the UID and GID configured in `.env`:

```dotenv
MNEMO_UID=0
MNEMO_GID=0
```

The compatibility default is root (`0:0`). For production, create a dedicated
host account and set these values to its numeric UID and GID:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin mnemosyne
id mnemosyne
```

For example:

```dotenv
MNEMO_UID=991
MNEMO_GID=991
```

The configured identity must be able to write `STATE_DB_PATH`. Data is
bind-mounted per component (ADR-015) under `MNEMO_DATA_DIR` (default
`./data`), so create and assign each component's subdirectory before
starting:

```bash
sudo install -d -o 991 -g 991 -m 700 /srv/mnemosyne/data/mnemo-core
sudo install -d -o 991 -g 991 -m 700 /srv/mnemosyne/data/mnemo-curator
```

Set `MNEMO_DATA_DIR=/srv/mnemosyne/data` in `.env` to point at them. Data
created previously under root ownership may also need a one-time ownership
change before switching to a non-root UID/GID. Confirm the active identity
after startup:

```bash
docker compose exec core id
```

The UID/GID need not have a named account inside the container; Docker can run
the process directly using numeric IDs.

## Observability

Set:

```dotenv
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
GRAFANA_ADMIN_PASSWORD=replace-with-a-long-random-value
```

Replace the example Grafana password with a long random value before starting
the profile.

Then start the optional profile:

```bash
docker compose --profile observability up --build
```

- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>

Grafana and Prometheus are bound to `127.0.0.1`. The OpenTelemetry collector
is available only on the internal Compose network. To expose any observability
service remotely, place it behind an authenticated TLS reverse proxy rather
than changing its host binding directly.

## Curator

`mnemo-curator` is optional. It scans Git-backed Markdown content, records
findings through the configured issue tracker, and can submit safe fixes
through `mnemo-core`.

Run a one-off scan:

```bash
docker compose --profile curator run --rm curator
```

To attempt inline fixes after issue creation:

```bash
docker compose --profile curator run --rm curator mnemo-curator scan --resolve
```

Semantic rewrites require `CURATOR_SEMANTIC_RESOLUTION_ENABLED=true` and an
approved OpenAI-compatible provider configured with `OPENAI_API_KEY`,
`OPENAI_BASE_URL`, and `OPENAI_MODEL`.

Set `CURATOR_ISSUE_TRACKER` to `github`, `jira`, or `sqlite`. The SQLite
fallback stores findings under `$MNEMO_DATA_DIR/mnemo-curator/mnemo-curator-issues.db`
(ADR-015).
