import pytest

from mnemo_core.api.deps import build_runner
from mnemo_core.pipeline import ProcessingError
from tests.conftest import FakeLLM, FakePublisher, llm_json_response, sample_input


async def test_process_does_not_publish():
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    doc = await runner.process(sample_input())
    assert doc.title == "Deploy the app"
    assert publisher.last_doc is None


async def test_run_processes_then_publishes():
    llm = FakeLLM(llm_json_response())
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    result = await runner.run(sample_input())

    assert publisher.last_doc is not None
    assert publisher.last_doc.title == "Deploy the app"
    assert result.publish.pr_url == "https://github.com/acme/kb/pull/1"


async def test_process_raises_pipeline_error_on_bad_json():
    llm = FakeLLM("not-json")
    publisher = FakePublisher()
    runner = build_runner(publisher=publisher, llm=llm)

    with pytest.raises(ProcessingError):
        await runner.process(sample_input())
