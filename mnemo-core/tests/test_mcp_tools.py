import asyncio

from fastapi.testclient import TestClient

from mnemo_core.api.app import create_app
from mnemo_core.api.deps import build_runner
from mnemo_core.jobs import JobManager, JobStore
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


async def test_submit_document_tool_queues_durable_ingest(configured_settings, tmp_path):
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=llm)
    manager = JobManager(JobStore(str(tmp_path / "state.db")))

    result = await handle_tool(
        "submit_document",
        {"content": "hello"},
        runner,
        manager,
    )

    assert publisher.last_doc is None
    assert "Document accepted for durable ingestion" in result[0].text
    assert "Job:" in result[0].text

    await asyncio.gather(*manager._tasks.values())
    assert publisher.last_doc is not None
    jobs = manager.store.list_jobs(actor="mcp")
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["result"]["publish"]["pr_url"] == "https://github.com/acme/kb/pull/1"


async def test_submit_document_tool_records_processing_failure(configured_settings, tmp_path):
    class FailingLLM(FakeLLM):
        async def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
            raise RuntimeError("processing failed")

    publisher = FakePublisher()
    runner = build_runner(configured_settings, publisher=publisher, llm=FailingLLM(""))
    manager = JobManager(JobStore(str(tmp_path / "state.db")), max_attempts=1)

    result = await handle_tool(
        "submit_document",
        {"content": "hello"},
        runner,
        manager,
    )

    assert "Document accepted for durable ingestion" in result[0].text
    await asyncio.gather(*manager._tasks.values())
    assert publisher.last_doc is None
    jobs = manager.store.list_jobs(actor="mcp")
    assert jobs[0]["status"] == "failed"
    assert jobs[0]["error"] == "processing failed"


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
