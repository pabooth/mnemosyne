from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import RootModel

from ...jobs import JobManager
from ...models import DocumentInput
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

router = APIRouter(prefix="/jobs")


class DocumentBatch(RootModel[list[DocumentInput]]):
    pass


def _manager(request: Request) -> JobManager:
    return request.app.state.job_manager


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", "shared-token")


def _can_access(request: Request, job: dict) -> bool:
    return getattr(request.state, "role", "") == "admin" or job["actor"] == _actor(request)


@router.post("", status_code=202)
async def create_job(
    document: DocumentInput,
    request: Request,
    kind: Literal["process", "ingest"] = Query(default="ingest"),
    runner: PipelineRunner = Depends(get_runner),
) -> dict:
    return _manager(request).submit(kind, _actor(request), document, runner)


@router.post("/batch", status_code=202)
async def create_batch(
    batch: DocumentBatch,
    request: Request,
    kind: Literal["process", "ingest"] = Query(default="ingest"),
    runner: PipelineRunner = Depends(get_runner),
) -> dict:
    if not batch.root or len(batch.root) > 50:
        raise HTTPException(status_code=422, detail="Batch must contain between 1 and 50 documents")
    jobs = [
        _manager(request).submit(kind, _actor(request), document, runner)
        for document in batch.root
    ]
    return {"jobs": jobs}


@router.get("")
async def list_jobs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    actor = None if getattr(request.state, "role", "") == "admin" else _actor(request)
    return _manager(request).store.list_jobs(actor=actor, limit=limit)


@router.get("/{job_id}")
async def get_job(job_id: str, request: Request) -> dict:
    job = _manager(request).store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access(request, job):
        raise HTTPException(status_code=403, detail="Job belongs to another actor")
    return job


@router.delete("/{job_id}", status_code=202)
async def cancel_job(job_id: str, request: Request) -> dict:
    job = _manager(request).store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access(request, job):
        raise HTTPException(status_code=403, detail="Job belongs to another actor")
    if not _manager(request).cancel(job_id):
        raise HTTPException(status_code=409, detail="Job is not currently running")
    return {"id": job_id, "status": "cancelling"}
