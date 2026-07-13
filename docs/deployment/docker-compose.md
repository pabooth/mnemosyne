# Deploy with Docker Compose

## Prerequisites

- Docker Engine with Docker Compose
- Credentials for one configured LLM provider
- A GitHub token with permission to create branches, files, and pull requests

## Set up the instance directory

All instance state — configuration and data — lives in one directory
located by `MNEMO_HOME` (ADR-017): `$MNEMO_HOME/mnemosyne.env` plus
`$MNEMO_HOME/data/<component>/`. Conventionally `~/mnemosyne` on a
development machine, `/srv/mnemosyne` on a Linux server.

```bash
mkdir -p ~/mnemosyne
cp mnemosyne.env.example ~/mnemosyne/mnemosyne.env
```

Add to your shell profile (and run now):

```bash
export MNEMO_HOME="$HOME/mnemosyne"
export COMPOSE_ENV_FILES="$MNEMO_HOME/mnemosyne.env"
```

Compose fails with an instructive error if `MNEMO_HOME` is unset — there is
deliberately no fallback into the source tree. Data on another disk is
handled by symlinking `$MNEMO_HOME/data`.

## Start Mnemosyne

Set `MNEMO_API_TOKEN`, `GITHUB_TOKEN`, `GITHUB_REPO`, and the credentials for
your selected LLM provider in `$MNEMO_HOME/mnemosyne.env`, then run:

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
the same API token configured in `$MNEMO_HOME/mnemosyne.env`.

The core API is also available directly at <http://localhost:7777>. Its host
port is bound to `127.0.0.1`, so it is not reachable from other machines.
Production deployments should expose only `mnemo-proxy` (or an equivalent
site-managed ingress).

Host bindings can be configured in `$MNEMO_HOME/mnemosyne.env`:

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

The core container uses the UID and GID configured in
`$MNEMO_HOME/mnemosyne.env`:

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
bind-mounted per component (ADR-015) under `$MNEMO_HOME/data`, so create
and assign each component's subdirectory before starting:

```bash
sudo install -d -o 991 -g 991 -m 700 "$MNEMO_HOME/data/mnemo-core"
sudo install -d -o 991 -g 991 -m 700 "$MNEMO_HOME/data/mnemo-curator"
```

Data created previously under root ownership may also need a one-time
ownership change before switching to a non-root UID/GID. Confirm the
active identity after startup:

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
fallback stores findings under `$MNEMO_HOME/data/mnemo-curator/issues.db`
(ADR-015/ADR-017).

## Migrating from earlier data layouts

Skip this section for new deployments. Earlier layouts predate the
instance directory (ADR-017) and ADR-015's per-component directories, and
none of them migrate automatically — starting the new layout without
migrating gives you empty databases, which for the vector index means
re-spending embedding-provider budget to rebuild it.

All migrations happen with services stopped (`docker compose down`) and
end at the same target layout:

```
$MNEMO_HOME/
├── mnemosyne.env
└── data/
    ├── mnemo-core/        # state.db, vectors.db
    └── mnemo-curator/     # issues.db (sqlite tracker only)
```

**From a checkout-resident layout** (`.env` and `./data` inside the
repository): move config and data into the instance directory, renaming
the databases to their ADR-017 names, with `-wal`/`-shm` siblings kept
beside their `.db`:

```bash
mkdir -p "$MNEMO_HOME/data/mnemo-core" "$MNEMO_HOME/data/mnemo-curator"
mv .env "$MNEMO_HOME/mnemosyne.env"

for ext in "" -wal -shm; do
  mv "./data/mnemo-core/mnemosyne.db$ext" "$MNEMO_HOME/data/mnemo-core/state.db$ext" 2>/dev/null || true
  mv "./data/mnemo-core/vectors.db$ext" "$MNEMO_HOME/data/mnemo-core/vectors.db$ext" 2>/dev/null || true
  mv "./data/mnemo-curator/mnemo-curator-issues.db$ext" "$MNEMO_HOME/data/mnemo-curator/issues.db$ext" 2>/dev/null || true
done
```

Flat pre-ADR-015 layouts (database files directly in `./data`) use the
same commands with the `mnemo-core`/`mnemo-curator` path segments dropped
from the sources.

**From named Docker volumes** (deployments created before ADR-015): data
lived in Docker-managed volumes rather than host directories. Copy each
volume's contents out, then apply the renames. The volume names carry the
Compose project prefix, so list them first:

```bash
docker volume ls --format '{{.Name}}' | grep mnemo
```

Then, substituting the names you found:

```bash
mkdir -p "$MNEMO_HOME/data/mnemo-core" "$MNEMO_HOME/data/mnemo-curator"
docker run --rm \
  -v mnemosyne_mnemo-data:/from:ro -v "$MNEMO_HOME/data/mnemo-core":/to \
  alpine sh -c 'cp -a /from/. /to/'
docker run --rm \
  -v mnemosyne_mnemo-curator-data:/from:ro -v "$MNEMO_HOME/data/mnemo-curator":/to \
  alpine sh -c 'cp -a /from/. /to/'

for ext in "" -wal -shm; do
  mv "$MNEMO_HOME/data/mnemo-core/mnemosyne.db$ext" "$MNEMO_HOME/data/mnemo-core/state.db$ext" 2>/dev/null || true
  mv "$MNEMO_HOME/data/mnemo-curator/mnemo-curator-issues.db$ext" "$MNEMO_HOME/data/mnemo-curator/issues.db$ext" 2>/dev/null || true
done
```

Moving `-wal`/`-shm` files together with their `.db` is safe here because
the services are stopped; SQLite reconciles them on next open.

In both cases, verify before bringing services back up, and only delete
old volumes once the migrated deployment has been confirmed working:

```bash
sqlite3 "$MNEMO_HOME/data/mnemo-core/state.db" "PRAGMA integrity_check;"
docker compose up -d
docker volume rm mnemosyne_mnemo-data mnemosyne_mnemo-curator-data
```
