from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DiataxisType = Literal["tutorial", "how-to", "reference", "explanation"]
ReviewTier = Literal["tier-1", "tier-2"]
ReviewVerdict = Literal["accept", "reject"]

MAX_DOCUMENT_CHARS = 1_000_000
MAX_BODY_CHARS = 1_000_000


def _validate_bounded_strings(values: list[str], label: str) -> list[str]:
    cleaned = [value.strip() for value in values]
    if any(not value or len(value) > 200 for value in cleaned):
        raise ValueError(f"{label} must contain between 1 and 200 characters")
    return cleaned


class DocumentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(default="", max_length=200)
    owner: str = Field(default="", max_length=100)
    type: DiataxisType | Literal[""] = ""
    sub_label: str = Field(default="", max_length=100, pattern=r"^[\w ./-]*$")
    content: str = Field(min_length=1, max_length=MAX_DOCUMENT_CHARS)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class DuplicateCandidate(BaseModel):
    """A possible existing-KB match surfaced by the read-path dedup check.

    ``score`` is the vector index's raw distance (lower is more similar for
    the sqlite-vec reference implementation); it is not a normalised
    similarity percentage.
    """

    path: str
    score: float


class ProcessedDocument(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    type: DiataxisType
    # Assigned by template lookup after classification (ADR-019), never by
    # the LLM. The tier-2 default fails closed for legacy records and for
    # documents with no matching template.
    review_tier: ReviewTier = "tier-2"
    sub_label: str = Field(default="", max_length=100, pattern=r"^[\w ./-]*$")
    status: Literal["draft", "review"] = "draft"
    tags: list[str] = Field(max_length=25)
    summary: str = Field(min_length=1, max_length=1_000)
    owner: str = Field(min_length=1, max_length=100)
    last_reviewed: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    flags: list[str] = Field(max_length=50)
    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    duplicate_candidates: list[DuplicateCandidate] = Field(default_factory=list)

    @field_validator("tags", "flags")
    @classmethod
    def validate_list_values(cls, values: list[str]) -> list[str]:
        return _validate_bounded_strings(values, "list values")


class PublishResult(BaseModel):
    pr_url: str
    branch: str
    file_path: str
    review: "AdversarialReviewResult | None" = None


class ReviewerReport(BaseModel):
    role: Literal["advocate", "critic"]
    provider_family: str
    verdict: ReviewVerdict
    recommended_tier: ReviewTier
    concerns: list[str] = Field(default_factory=list, max_length=50)
    rationale: str = Field(min_length=1, max_length=4_000)

    @field_validator("concerns")
    @classmethod
    def validate_concerns(cls, values: list[str]) -> list[str]:
        return _validate_bounded_strings(values, "concerns")


class AdversarialReviewResult(BaseModel):
    tier: ReviewTier
    advocate: ReviewerReport | None = None
    critic: ReviewerReport | None = None
    outcome: Literal["accepted", "rejected", "escalated"]
    requires_human_review: bool
    merged: bool = False
    reason: str


class IngestResult(BaseModel):
    document: ProcessedDocument
    publish: PublishResult
    review: AdversarialReviewResult | None = None


class IndexTriggerRequest(BaseModel):
    """On-demand reindex of content that just merged."""

    commit_sha: str = Field(default="", max_length=64)
    paths: list[str] = Field(default_factory=list, max_length=500)


class IndexReconcileRequest(BaseModel):
    """Force a reconciliation pass: diff the repo at main against the
    Vector DB by content hash and process only what is missing."""

    dry_run: bool = False


class IndexResult(BaseModel):
    chunks: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0
    unchanged: int = 0
