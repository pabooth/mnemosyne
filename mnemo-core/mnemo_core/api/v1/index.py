from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/index")


class IndexTriggerRequest(BaseModel):
    """On-demand reindex of content that just merged."""

    commit_sha: str = Field(default="", max_length=64)
    paths: list[str] = Field(default_factory=list, max_length=500)


class IndexReconcileRequest(BaseModel):
    """Force a reconciliation pass: diff the repo at main against the
    Vector DB by SHA/hash and process only what is missing."""

    dry_run: bool = False


@router.post("/trigger", status_code=202)
async def trigger_index(payload: IndexTriggerRequest, request: Request) -> dict:
    """Contract stub (ADR-013): queues an index_trigger job. No indexing logic exists yet."""
    return request.app.state.job_manager.submit(
        "index_trigger", getattr(request.state, "actor", "shared-token"), payload
    )


@router.post("/reconcile", status_code=202)
async def reconcile_index(payload: IndexReconcileRequest, request: Request) -> dict:
    """Contract stub (ADR-013): queues an index_reconcile job. No indexing logic exists yet."""
    return request.app.state.job_manager.submit(
        "index_reconcile", getattr(request.state, "actor", "shared-token"), payload
    )
