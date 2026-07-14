from datetime import date

import pytest

from mnemo_core.pipeline import ProcessingError
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


def test_build_system_prompt_lists_kb_sub_labels_type_qualified():
    prompt = build_system_prompt(SAMPLE_TEMPLATES)
    assert "how-to / procedure:" in prompt
    assert "reference / standard:" in prompt
    assert "RFC 2119" in prompt  # the KB-authored description, unchanged
    assert "never pair a sub-type with a different type" in prompt


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


async def test_classify_selects_template_body_from_classified_result_without_hints():
    llm = FakeLLM(llm_json_response())
    await classify_augment_format(sample_input(), llm, SAMPLE_TEMPLATES)
    assert len(llm.calls) == 2
    assert "Use this template" not in llm.calls[0][1]
    assert "## Verification" in llm.last_user


async def test_classify_does_not_use_stale_hinted_template():
    llm = FakeLLM(llm_json_response(type="reference", sub_label="standard"))
    doc = sample_input(type="how-to", sub_label="procedure")
    await classify_augment_format(doc, llm, SAMPLE_TEMPLATES)
    assert "## Policies" in llm.last_user
    assert "## Verification" not in llm.last_user


async def test_classify_rejects_sub_label_not_defined_for_type():
    llm = FakeLLM(llm_json_response(type="reference", sub_label="procedure"))
    with pytest.raises(ProcessingError, match="does not define for type 'reference'"):
        await classify_augment_format(sample_input(), llm, SAMPLE_TEMPLATES)


async def test_classify_rejects_any_sub_label_under_empty_taxonomy():
    llm = FakeLLM(llm_json_response(type="how-to", sub_label="procedure"))
    with pytest.raises(ProcessingError, match="does not define"):
        await classify_augment_format(sample_input(), llm, TemplateSet([]))


async def test_classify_accepts_empty_sub_label():
    llm = FakeLLM(llm_json_response(sub_label=""))
    doc = await classify_augment_format(sample_input(), llm, TemplateSet([]))
    assert doc.sub_label == ""


async def test_review_tier_comes_from_template_not_llm():
    # ADR-019: the LLM claims tier-1, but "standard" is declared tier-2.
    llm = FakeLLM(
        llm_json_response(type="reference", sub_label="standard", review_tier="tier-1")
    )
    doc = await classify_augment_format(sample_input(), llm, SAMPLE_TEMPLATES)
    assert doc.review_tier == "tier-2"


async def test_review_tier_uses_declared_tier_1():
    llm = FakeLLM(
        llm_json_response(type="how-to", sub_label="procedure", review_tier="tier-2")
    )
    doc = await classify_augment_format(sample_input(), llm, SAMPLE_TEMPLATES)
    assert doc.review_tier == "tier-1"


async def test_review_tier_fails_closed_without_matching_template():
    llm = FakeLLM(llm_json_response(sub_label="", review_tier="tier-1"))
    doc = await classify_augment_format(sample_input(), llm, TemplateSet([]))
    assert doc.review_tier == "tier-2"


def test_classifier_prompt_does_not_ask_for_review_tier():
    assert "review_tier" not in build_system_prompt(SAMPLE_TEMPLATES)
