from fastapi import APIRouter, Depends, Request

from ...indexing.service import Indexer
from ...models import IndexReconcileRequest, IndexTriggerRequest
from ..deps import get_indexer

router = APIRouter(prefix="/index")


@router.post("/trigger", status_code=202)
async def trigger_index(
    payload: IndexTriggerRequest,
    request: Request,
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    return request.app.state.job_manager.submit(
        "index_trigger",
        getattr(request.state, "actor", "shared-token"),
        payload,
        indexer=indexer,
    )


@router.post("/reconcile", status_code=202)
async def reconcile_index(
    payload: IndexReconcileRequest,
    request: Request,
    indexer: Indexer = Depends(get_indexer),
) -> dict:
    return request.app.state.job_manager.submit(
        "index_reconcile",
        getattr(request.state, "actor", "shared-token"),
        payload,
        indexer=indexer,
    )
