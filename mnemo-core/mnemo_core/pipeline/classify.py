from ..llm.base import LLMProvider
from ..models import DocumentInput, ProcessedDocument
from .parse import parse_processed_document
from .prompts import build_system_prompt, build_user_message
from .templates import TemplateSet


async def classify_augment_format(
    doc: DocumentInput, llm: LLMProvider, templates: TemplateSet
) -> ProcessedDocument:
    template = (
        templates.get(doc.type, doc.sub_label) if doc.type and doc.sub_label else None
    )
    user_message = build_user_message(doc, template)
    raw = await llm.complete(build_system_prompt(templates), user_message)
    return parse_processed_document(raw)
