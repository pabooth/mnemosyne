# mnemo-core

`mnemo-core` is the backend service for
[Mnemosyne](https://github.com/pabooth/mnemosyne), an AI-assisted document
ingestion engine.

It provides:

- a FastAPI REST interface;
- an MCP intake server;
- document classification and processing;
- durable jobs and audit history;
- GitHub pull-request publishing with mandatory human review.

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
