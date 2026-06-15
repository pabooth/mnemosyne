from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner
from mnemo_core.mcp.server import _mounted_path, handle_tool
from tests.conftest import FakeLLM, FakePublisher, llm_json_response


async def test_process_document_tool(configured_settings):
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)

    result = await handle_tool(
        "process_document",
        {"content": "hello"},
        runner,
    )

    assert publisher.last_doc is None
    assert "Deploy the app" in result[0].text


async def test_submit_document_tool(configured_settings):
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)

    result = await handle_tool(
        "submit_document",
        {"content": "hello"},
        runner,
    )

    assert publisher.last_doc is not None
    assert "https://github.com/acme/kb/pull/1" in result[0].text


def test_mcp_sse_route_reaches_auth(configured_settings):
    app = create_app(configured_settings)
    with TestClient(app) as client:
        response = client.get("/mcp/sse")

    assert response.status_code == 401
    assert response.text == "Invalid or missing bearer token"


def test_mcp_messages_route_reaches_auth(configured_settings):
    app = create_app(configured_settings)
    with TestClient(app) as client:
        response = client.post("/mcp/messages")

    assert response.status_code == 401
    assert response.text == "Invalid or missing bearer token"


def test_mounted_path_strips_root_path_prefix():
    assert _mounted_path({"path": "/mcp/sse", "root_path": "/mcp"}) == "/sse"
    assert _mounted_path({"path": "/sse", "root_path": ""}) == "/sse"
