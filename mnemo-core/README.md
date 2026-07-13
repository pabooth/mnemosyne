# mnemo-core

`mnemo-core` is the backend service for
[Mnemosyne](https://github.com/pabooth/mnemosyne), an AI-assisted document
ingestion engine.

It provides:

- a FastAPI REST interface versioned under `/api/v1`;
- an MCP intake server;
- document classification and processing;
- durable jobs and admin audit history;
- cross-family adversarial review with Tier 1 auto-merge and Tier 2 human gates;

The REST API keeps infrastructure probes unversioned at `/health` and
`/ready`. Content and job routes live under `/api/v1`, including synchronous
`/process`, `/ingest`, and `/publish`, durable `/jobs`, source intake under
`/sources`, signed GitHub webhooks under `/webhooks/github`, admin audit at
`/audit`, and indexer contract stubs at `/index/trigger` and
`/index/reconcile`.

For installation, configuration, deployment, security guidance, and complete
project documentation, see the
[Mnemosyne repository](https://github.com/pabooth/mnemosyne).

## Development

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## License

MIT. See [LICENSE](LICENSE).
