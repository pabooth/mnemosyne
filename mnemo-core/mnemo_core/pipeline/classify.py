from ..llm.base import LLMProvider
from ..models import DocumentInput, ProcessedDocument
from .parse import parse_processed_document
from .prompts import SYSTEM_PROMPT, build_user_message


async def classify_augment_format(doc: DocumentInput, llm: LLMProvider) -> ProcessedDocument:
    user_message = build_user_message(doc)
    raw = await llm.complete(SYSTEM_PROMPT, user_message)
    return parse_processed_document(raw)
