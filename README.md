![Mnemosyne](./header.png)

![License](https://img.shields.io/badge/license-MIT-blue)
![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/badge/version-0.1.0-orange)

---

Mnemosyne is an open source, AI-assisted knowledge management system.

Feed it a document and it classifies it by type — reference, how-to, tutorial, or explanation — according to the [Diátaxis framework](https://diataxis.fr). It corrects spelling and grammar, flags gaps, enriches with metadata, and opens a pull request for human review.

Nothing reaches your knowledge base without approval.

Mnemosyne ships as two components: **mnemo-ui**, a web interface, and **mnemo-core**, the backend engine. Core can be accessed programmatically via REST API, or integrated with your AI assistant via MCP.

Built for teams that care about the quality and governance of their knowledge, not just the volume of it.

---

## Roadmap

- [ ] GitHub webhook intake
- [ ] Pluggable LLM provider support
- [ ] Self-audit capability — staleness detection, gap analysis, and cross-reference checking
- [ ] Observability via OpenTelemetry with a reference Prometheus/Grafana stack
- [ ] `.deb` / `.rpm` packaging
- [ ] Additional knowledge base provider documentation (Docusaurus, VitePress, Obsidian, SharePoint)

---

## Architecture

For a full description of Mnemosyne's architecture, component design, and architectural decisions, see [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

---

## Installation

> Full installation and deployment guides are coming soon. In the meantime, see [`/deploy`](./deploy) for Docker and reverse proxy configurations.

### Prerequisites

- Docker and Docker Compose
- An Anthropic API key

### Quick start

```bash
# Coming soon
```

---

## Configuration

> Full configuration reference coming soon.

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | — |
| `MNEMO_PORT_UI` | mnemo-ui port | `8888` |
| `MNEMO_PORT_CORE` | mnemo-core port | `7777` |

### MCP integration

mnemo-core exposes an MCP server for intake. Connect it to your AI assistant to submit documents directly from your workflow.

> MCP configuration guide coming soon.

---

## Contributing

> Contributing guidelines coming soon.

We welcome contributions. Please open an issue before submitting a pull request for anything beyond small fixes.

---

## License

Mnemosyne is released under the [MIT License](./LICENSE).

