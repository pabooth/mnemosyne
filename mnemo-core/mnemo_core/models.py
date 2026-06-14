from pydantic import BaseModel


class DocumentInput(BaseModel):
    title: str = ""
    owner: str = ""
    type: str = ""
    sub_label: str = ""
    content: str


class ProcessedDocument(BaseModel):
    title: str
    type: str
    sub_label: str = ""
    status: str = "draft"
    tags: list[str]
    summary: str
    owner: str
    last_reviewed: str
    flags: list[str]
    body: str


class PublishResult(BaseModel):
    pr_url: str
    branch: str
    file_path: str


class IngestResult(BaseModel):
    document: ProcessedDocument
    publish: PublishResult
