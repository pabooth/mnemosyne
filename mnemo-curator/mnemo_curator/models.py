from typing import Literal

from pydantic import BaseModel, Field

FindingKind = Literal[
    "missing-owner",
    "stale",
    "invalid-review-date",
    "broken-relative-link",
    "duplicate-title",
    "semantic-gap",
]

FindingSeverity = Literal["low", "medium", "high"]
ResolutionStatus = Literal["submitted", "skipped", "failed"]


class Document(BaseModel):
    path: str = Field(min_length=1)
    content: str = Field(min_length=1)


class Finding(BaseModel):
    kind: FindingKind
    severity: FindingSeverity = "medium"
    path: str = ""
    title: str = ""
    detail: str = ""
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
    issue_url: str = ""


class Resolution(BaseModel):
    finding: Finding
    status: ResolutionStatus
    reason: str = ""
    submitted_job_id: str = ""
    corrected_content: str = ""


class CuratorReport(BaseModel):
    repository: str
    documents_scanned: int
    findings: list[Finding]
    resolutions: list[Resolution] = Field(default_factory=list)
