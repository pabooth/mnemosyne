from datetime import date

from mnemo_core.pipeline.classify import classify_augment_format
from mnemo_core.pipeline.prompts import build_system_prompt, build_user_message
from mnemo_core.pipeline.templates import TemplateSet
from tests.conftest import SAMPLE_TEMPLATES, FakeLLM, llm_json_response, sample_input


def test_build_user_message_includes_hints_and_template():
    doc = sample_input(
        title="My Doc",
        owner="team-a",
        type="reference",
        sub_label="standard",
        content="Policy text",
    )
    template = SAMPLE_TEMPLATES.get("reference", "standard")
    message = build_user_message(doc, template, today=date(2026, 6, 14))
    assert "Title hint: My Doc" in message
    assert "Diataxis type hint: reference" in message
    assert template.body in message


def test_build_user_message_without_template_has_no_template_block():
    message = build_user_message(sample_input(), None, today=date(2026, 6, 14))
    assert "Use this template" not in message


def test_build_system_prompt_lists_kb_sub_labels():
    prompt = build_system_prompt(SAMPLE_TEMPLATES)
    assert '"procedure"' in prompt
    assert '"standard"' in prompt
    assert "RFC 2119" in prompt  # the KB-authored description, verbatim


def test_build_system_prompt_with_empty_taxonomy():
    prompt = build_system_prompt(TemplateSet([]))
    assert 'always ""' in prompt
    assert "Diataxis" in prompt


async def test_classify_augment_format_parses_llm_response():
    llm = FakeLLM(llm_json_response(title="Parsed Title"))
    doc = await classify_augment_format(sample_input(), llm, SAMPLE_TEMPLATES)
    assert doc.title == "Parsed Title"
    assert llm.last_system is not None
    assert "Diataxis" in llm.last_system


async def test_classify_includes_template_body_when_hinted():
    llm = FakeLLM(llm_json_response())
    doc = sample_input(type="how-to", sub_label="procedure")
    await classify_augment_format(doc, llm, SAMPLE_TEMPLATES)
    assert "## Verification" in llm.last_user
