from ..llm.base import LLMProvider
from ..models import DocumentInput, ProcessedDocument
from . import ProcessingError
from .parse import parse_processed_document
from .prompts import build_system_prompt, build_user_message
from .templates import TemplateSet

DOCUMENT_OUTPUT_MAX_TOKENS = 16_000


async def classify_augment_format(
    doc: DocumentInput, llm: LLMProvider, templates: TemplateSet
) -> ProcessedDocument:
    system_prompt = build_system_prompt(templates)
    raw = await llm.complete(
        system_prompt,
        build_user_message(doc),
        max_tokens=DOCUMENT_OUTPUT_MAX_TOKENS,
    )
    result = _validate_taxonomy(parse_processed_document(raw), templates)

    template = templates.get(result.type, result.sub_label) if result.sub_label else None
    if template is not None:
        raw = await llm.complete(
            system_prompt,
            build_user_message(doc, template),
            max_tokens=DOCUMENT_OUTPUT_MAX_TOKENS,
        )
        result = _validate_taxonomy(parse_processed_document(raw), templates)
        template = templates.get(result.type, result.sub_label) if result.sub_label else None

    # ADR-019: the template declaration is the canonical review tier; the
    # model has no say. Documents with no matching template fail closed.
    return result.model_copy(
        update={"review_tier": template.tier if template is not None else "tier-2"}
    )


def _validate_taxonomy(
    result: ProcessedDocument, templates: TemplateSet
) -> ProcessedDocument:

    # LLM output is untrusted: a sub-label is only valid for the type it is
    # defined under in the KB's template set (ADR-018). Failing here lets the
    # durable-job retry give the model a second attempt.
    if result.sub_label and templates.get(result.type, result.sub_label) is None:
        valid = [t.sub_label for t in templates.for_type(result.type)]
        raise ProcessingError(
            f"LLM returned sub_label {result.sub_label!r}, which this knowledge "
            f"base does not define for type {result.type!r}; valid sub-labels "
            f"for {result.type!r}: {valid or 'none'}"
        )
    return result
