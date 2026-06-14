import json
import re

from ..models import ProcessedDocument
from . import ProcessingError


def strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    return re.sub(r"\s*```$", "", raw)


def parse_processed_document(raw: str) -> ProcessedDocument:
    cleaned = strip_json_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ProcessingError(
            f"LLM returned invalid JSON: {e}\n\nRaw response:\n{cleaned[:500]}"
        ) from e

    try:
        return ProcessedDocument(**data)
    except Exception as e:
        raise ProcessingError(f"LLM response missing required fields: {e}") from e
