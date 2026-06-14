# Architecture

Mnemosyne (mnemo) is an AI-assisted document ingestion engine. It accepts raw documents from multiple intake sources, classifies and augments them using a pluggable LLM, and raises pull requests for human review before content is committed to a knowledge base.

Mnemosyne is not a knowledge base. It is the pipeline that feeds one.

***

## System Overview

```mermaid
flowchart TB
    subgraph CLIENTS["Intake Clients"]
        UI["Web UI\n(optional)"]
        MCP_CLIENT["AI Agent\n(any MCP client)"]
        API_CLIENT["Programmatic Client"]
        GIT_WEBHOOK["Git Webhook\n(push to watched branch)"]
    end

    subgraph PROXY["Reverse Proxy (optional, production only)"]
        RP["Reverse Proxy"]
    end

    subgraph CORE["mnemo-core"]
        REST["REST API\npreview and ingest"]
        MCP_SERVER["MCP Server"]
        METRICS["Metrics and Traces\n(OpenTelemetry)"]
        subgraph PIPELINE["Ingestion Pipeline"]
            CLASSIFY["Diataxis Classification"]
            AUGMENT["Content Augmentation"]
            FORMAT["Format and Structure"]
            PREVIEW["Preview Response"]
            COMMIT["Internal Publish\nCommit and Raise PR"]
        end
    end

    subgraph LLM["LLM (pluggable)"]
        AI["LLM Provider"]
    end

    subgraph REVIEW["Human Review"]
        PR["Pull Request"]
        HUMAN["Human Approves and Merges"]
    end

    subgraph STORE["Content Store"]
        GIT["Git Repository"]
    end

    subgraph KB["KB Layer (pluggable)"]
        KB_NODE["KB Provider"]
    end

    subgraph OBS["Observability (optional)"]
        direction LR
        OTEL["OpenTelemetry Collector"]
        PROM["Prometheus"]
        GRAFANA["Grafana"]
    end

    BROWSER(["Browser / User"])

    BROWSER -->|production| RP
    RP -->|"/"| UI
    RP -->|"/api/"| REST
    BROWSER -->|dev direct| UI
    UI --> REST

    MCP_CLIENT -->|MCP protocol| MCP_SERVER
    API_CLIENT -->|HTTP REST| REST
    GIT_WEBHOOK -->|HTTP webhook| REST

    REST --> PIPELINE
    MCP_SERVER --> PIPELINE

    CLASSIFY <--> AI
    AUGMENT <--> AI
    FORMAT <--> AI

    CLASSIFY --> AUGMENT --> FORMAT
    FORMAT -->|preview only| PREVIEW
    FORMAT -->|ingest workflow| COMMIT
    COMMIT <-->|commit and PR| GIT

    GIT --> PR
    PR --> HUMAN
    HUMAN -->|approve and merge| GIT

    GIT --> KB_NODE

    METRICS -->|OTLP| OTEL
    OTEL --> PROM
    PROM --> GRAFANA
```

***

## Components

### mnemo-core

The core ingestion engine. Exposes two intake interfaces — a REST API and an MCP server — both of which feed the same processing pipeline. Can be deployed and operated independently of the web UI.

The REST API has two external workflow shapes:

- `POST /api/process` accepts a raw document and returns a processed preview. It does not write to GitHub and does not raise a pull request.
- `POST /api/ingest` accepts a raw document, processes it, commits the processed output to a branch, and raises a pull request for human review.

Publishing is an internal capability of `mnemo-core`, used by the ingest workflow after processing. It is not exposed as a standalone public API operation.

### mnemo-ui

An optional web frontend for document submission and pipeline status. Communicates directly with mnemo-core via the REST API. In production, both are fronted by a reverse proxy.

### Ingestion Pipeline

The pipeline has a shared processing path and two outcomes:

1. **Diataxis Classification** — the document is classified into one of four Diataxis content types: tutorial, how-to, reference, or explanation. This step uses the LLM.
2. **Content Augmentation** — metadata, frontmatter, summaries, and tags are generated and applied. This step uses the LLM.
3. **Format and Structure** — the document is structured according to the target KB's conventions. This step uses the LLM.

After processing, the caller either receives a preview response or the ingest workflow continues to the internal publish step:

```text
Raw document -> process -> preview response

Raw document -> process -> internal publish -> branch + PR -> human review -> merge
```

The internal publish step commits the processed document to the Git content store and raises a pull request for human review. It is not a separately exposed intake method.

### LLM Layer

Pluggable. The reference implementation uses Anthropic's API. Alternative providers can be configured via environment variable. See ADR-004.

### Content Store

A Git repository. All KB content is stored as markdown files under version control. The ingest workflow commits processed documents to feature branches and raises pull requests; it never merges directly.

### KB Layer

Pluggable. Any tool that can serve markdown files from a Git repository can act as the KB layer. The reference implementation is MkDocs Material. See ADR-007 for supported options including SharePoint for enterprise deployments.

### Human Review

Every document submitted through the ingest workflow results in a pull request. A human must review and merge it. The pipeline has no merge permissions. This is a hard governance requirement, not a default setting. See ADR-005.

Preview-only processing is allowed as a non-mutating workflow for user interfaces and internal tooling. Preview output does not reach the KB unless it is later submitted through the governed ingest workflow.

### Reverse Proxy

Optional. Not required for local development. In production, a reverse proxy sits in front of both mnemo-ui and mnemo-core, routing `/` to the UI and `/api/` to the core. Stub configurations for common options are provided in `/deploy/reverse-proxy/`.

`mnemo-core` is intended to be private rather than directly exposed to the internet. Even so, REST and MCP intake endpoints should require a simple authentication layer so accidental exposure, misrouting, or lateral access does not grant unauthenticated access to LLM processing or PR creation.

### Observability

Optional. mnemo-core is instrumented with OpenTelemetry and emits traces, metrics, and structured logs. A reference Prometheus and Grafana stack is provided in `/deploy/observability/`. The OTLP endpoint is configurable, allowing export to any compatible backend.

***

## Intake Methods

| Method      | Interface  | Use case                                                                 |
| ----------- | ---------- | ------------------------------------------------------------------------ |
| Web UI      | REST API   | Manual document preview and governed submission via browser              |
| AI Agent    | MCP Server | Submission from Claude, ChatGPT, or any MCP-compatible agent             |
| API Client  | REST API   | CI/CD pipelines, scripts, webhooks, CLI                                  |
| Git Webhook | REST API   | Automatic ingestion on push to a watched branch                          |

External intake clients submit raw documents. They may either request a non-mutating processed preview or use the full ingest workflow that creates a pull request.

The MCP server is an intake interface only. It does not expose KB query or retrieval capabilities.

***

## Deployment

Mnemosyne is distributed as:

- Docker images (`mnemo-core`, `mnemo-ui`, `mnemo` combined)
- Release archives (`mnemo-core-x.x.x.tgz`, `mnemo-ui-x.x.x.tgz`, `mnemo-x.x.x.tgz`)

A `docker-compose.yml` in the root provides a local development environment. Production deployment options are documented in `/docs/deployment/`.

***

## Repo Structure

```typescript
/
├── mnemo-core/        # REST API, MCP server, ingestion pipeline
├── mnemo-ui/          # React web frontend
├── deploy/
│   ├── reverse-proxy/ # Stub configs: Caddy, nginx, Traefik
│   └── observability/ # Prometheus + Grafana stack
├── docs/
│   ├── adr/           # Architecture Decision Records
│   └── deployment/    # Deployment guides
├── docker-compose.yml # Local development
└── LICENSE
```

***

## Architecture Decision Records

Key decisions governing this project are documented as ADRs in `/docs/adr/`.

| ADR | Decision                                         | Status   |
| --- | ------------------------------------------------ | -------- |
| 001 | Monorepo with separate build artefacts           | Accepted |
| 002 | MIT License                                      | Accepted |
| 003 | Diataxis as content taxonomy                     | Accepted |
| 004 | Pluggable LLM layer                              | Accepted |
| 005 | AI must not contribute without human review      | Accepted |
| 006 | MCP as intake interface only, not retrieval      | Accepted |
| 007 | Pluggable KB layer, MkDocs Material as reference | Accepted |
