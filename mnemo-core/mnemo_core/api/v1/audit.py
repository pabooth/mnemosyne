from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/audit")


@router.get("")
async def list_audit(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    return request.app.state.job_store.list_audit(limit=limit)
