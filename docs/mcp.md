# MCP configuration

Mnemosyne exposes intake tools only:

- `process_document`: generate a preview without publishing
- `submit_document`: queue durable processing and pull-request creation

`submit_document` returns a job identifier immediately. Processing continues inside
`mnemo-core` after the MCP request ends, so client tool timeouts cannot cancel publication.
The pull request is created when the durable ingest job completes.

The network endpoint uses SSE:

```text
GET  https://mnemosyne.example.com/mcp/sse
POST https://mnemosyne.example.com/mcp/messages
```

Send the configured API token as:

```text
Authorization: Bearer <MNEMO_API_TOKEN>
```

Clients with remote SSE support should connect directly. Clients that support
only local stdio MCP servers require a thin SSE-to-stdio bridge. Such a bridge
must not contain Mnemosyne processing or publishing logic.
