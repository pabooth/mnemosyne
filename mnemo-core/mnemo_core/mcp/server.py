"""MCP server — intake interface only (ADR-006).

Exposes two tools:
  submit_document  — full pipeline (classify + augment + format + commit + PR)
  process_document — classify + augment + format only, no commit (preview mode)

Mounted as an ASGI sub-app at /mcp in the main FastAPI application.
Clients connect via SSE at /mcp/sse and POST messages to /mcp/messages.
Local stdio wrappers may bridge to these endpoints for clients that cannot
connect to network MCP servers directly; ingestion logic remains here.
"""

import json
from collections.abc import Callable

import mcp.types as types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from ..auth import auth_is_configured, bearer_token_is_valid
from ..config import get_settings
from ..models import DocumentInput
from ..pipeline import PipelineError
from ..pipeline.runner import PipelineRunner

_server = Server("mnemo-core")
_sse_transport = SseServerTransport("/messages")
_default_runner_factory: Callable[[], PipelineRunner] | None = None


def _runner_factory() -> PipelineRunner:
    if _default_runner_factory is not None:
        return _default_runner_factory()
    from ..api.deps import build_runner

    return build_runner(get_settings())


@_server.list_tools()
async def _list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="submit_document",
            description=(
                "Submit a document to the Mnemosyne ingestion pipeline. "
                "Classifies, augments, formats the document and raises a GitHub PR for human review. "
                "Returns the PR URL."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Raw document content (markdown or plain text)",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title hint — inferred from content if omitted",
                    },
                    "owner": {
                        "type": "string",
                        "description": "Document owner — defaults to 'unset'",
                    },
                    "type": {
                        "type": "string",
                        "description": "Diataxis type hint: tutorial | how-to | reference | explanation",
                    },
                    "sub_label": {
                        "type": "string",
                        "description": "Sub-label hint — inferred from content if omitted",
                    },
                },
                "required": ["content"],
            },
        ),
        types.Tool(
            name="process_document",
            description=(
                "Classify, augment, and format a document without committing it. "
                "Returns the structured document as JSON for review. No PR is raised."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Raw document content"},
                    "title": {"type": "string", "description": "Title hint (optional)"},
                    "owner": {"type": "string", "description": "Document owner (optional)"},
                    "type": {"type": "string", "description": "Diataxis type hint (optional)"},
                    "sub_label": {"type": "string", "description": "Sub-label hint (optional)"},
                },
                "required": ["content"],
            },
        ),
    ]


async def handle_tool(
    name: str,
    arguments: dict,
    runner: PipelineRunner,
) -> list[types.TextContent]:
    doc_input = DocumentInput(
        content=arguments["content"],
        title=arguments.get("title", ""),
        owner=arguments.get("owner", ""),
        type=arguments.get("type", ""),
        sub_label=arguments.get("sub_label", ""),
    )

    try:
        if name == "submit_document":
            result = await runner.run(doc_input)
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Document submitted successfully.\n"
                        f"PR: {result.publish.pr_url}\n"
                        f"Branch: {result.publish.branch}\n"
                        f"File: {result.publish.file_path}"
                    ),
                )
            ]
        if name == "process_document":
            doc = await runner.process(doc_input)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(doc.model_dump(), indent=2),
                )
            ]
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    except PipelineError as e:
        return [types.TextContent(type="text", text=f"Pipeline error: {e}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Unexpected error: {e}")]


@_server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    return await handle_tool(name, arguments, _runner_factory())


class _MCPASGIRouter:
    """Minimal ASGI router for the MCP SSE endpoints.

    Designed to be mounted at /mcp — Starlette strips the prefix so paths
    arrive here as /sse and /messages.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return

        path = _mounted_path(scope)
        method: str = scope.get("method", "").upper()

        if path == "/sse" and method == "GET":
            if not await _authorize(scope, receive, send):
                return
            async with _sse_transport.connect_sse(scope, receive, send) as streams:
                await _server.run(
                    streams[0],
                    streams[1],
                    _server.create_initialization_options(),
                )
        elif path == "/messages" and method == "POST":
            if not await _authorize(scope, receive, send):
                return
            await _sse_transport.handle_post_message(scope, receive, send)
        else:
            response = Response(status_code=404)
            await response(scope, receive, send)


async def _authorize(scope: Scope, receive: Receive, send: Send) -> bool:
    cfg = get_settings()
    if not auth_is_configured(cfg):
        response = Response("MNEMO_API_TOKEN is not configured", status_code=503)
        await response(scope, receive, send)
        return False

    authorization = _header(scope, b"authorization")
    if bearer_token_is_valid(authorization, cfg):
        return True

    response = Response(
        "Invalid or missing bearer token",
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
    )
    await response(scope, receive, send)
    return False


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin1")
    return None


def _mounted_path(scope: Scope) -> str:
    """Return the path relative to the mount point when Starlette keeps the prefix."""
    path: str = scope.get("path", "")
    root_path: str = scope.get("root_path", "")
    if root_path and path.startswith(root_path):
        return path[len(root_path):] or "/"
    return path


def create_mcp_asgi(
    runner_factory: Callable[[], PipelineRunner] | None = None,
) -> _MCPASGIRouter:
    global _default_runner_factory
    _default_runner_factory = runner_factory
    return _MCPASGIRouter()
