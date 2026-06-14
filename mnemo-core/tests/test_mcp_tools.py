from mnemo_core.api.deps import build_runner
from mnemo_core.mcp.server import handle_tool
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
