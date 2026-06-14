from datetime import date

import pytest

from mnemo_core.pipeline.classify import classify_augment_format
from mnemo_core.pipeline.prompts import STANDARD_TEMPLATE, build_user_message
from tests.conftest import FakeLLM, llm_json_response, sample_input


def test_build_user_message_includes_hints():
    doc = sample_input(
        title="My Doc",
        owner="team-a",
        type="reference",
        sub_label="standard",
        content="Policy text",
    )
    message = build_user_message(doc, today=date(2026, 6, 14))
    assert "Title hint: My Doc" in message
    assert "Diataxis type hint: reference" in message
    assert STANDARD_TEMPLATE.strip() in message


async def test_classify_augment_format_parses_llm_response():
    llm = FakeLLM(llm_json_response(title="Parsed Title"))
    doc = await classify_augment_format(sample_input(), llm)
    assert doc.title == "Parsed Title"
    assert llm.last_system is not None
    assert "Diataxis" in llm.last_system
