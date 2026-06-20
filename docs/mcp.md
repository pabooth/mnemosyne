# MCP configuration

Mnemosyne exposes intake tools only:

- `process_document`: generate a preview without publishing
- `submit_document`: process and create a pull request

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
