import pytest

from mnemo_core.pipeline import ProcessingError
from mnemo_core.pipeline.parse import parse_processed_document, strip_json_fences
from tests.conftest import VALID_PROCESSED_JSON, llm_json_response


def test_strip_json_fences():
    raw = '```json\n{"title": "x"}\n```'
    assert strip_json_fences(raw) == '{"title": "x"}'


def test_parse_processed_document_valid_json():
    doc = parse_processed_document(llm_json_response())
    assert doc.title == VALID_PROCESSED_JSON["title"]
    assert doc.type == "how-to"


@pytest.mark.parametrize(
    "status",
    ["draft", "review", "proposed", "accepted", "modified", "superseded"],
)
def test_parse_processed_document_accepts_document_statuses(status):
    doc = parse_processed_document(llm_json_response(status=status))
    assert doc.status == status


def test_parse_processed_document_fenced_json():
    doc = parse_processed_document(f"```json\n{llm_json_response()}\n```")
    assert doc.title == VALID_PROCESSED_JSON["title"]


def test_parse_processed_document_invalid_json():
    with pytest.raises(ProcessingError, match="invalid JSON"):
        parse_processed_document("not json")


def test_parse_processed_document_missing_fields():
    with pytest.raises(ProcessingError, match="missing required fields"):
        parse_processed_document('{"title": "only title"}')
