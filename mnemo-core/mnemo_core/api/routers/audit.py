from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...config import Settings, get_settings
from ...pipeline import PipelineError
from ...self_audit import audit_knowledge_base

router = APIRouter(prefix="/api/audit")


@router.get("")
async def list_audit(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict]:
    return request.app.state.job_store.list_audit(limit=limit)


@router.post("/knowledge-base")
async def run_knowledge_base_audit(
    cfg: Settings = Depends(get_settings),
) -> dict:
    try:
        return await audit_knowledge_base(cfg)
    except PipelineError as error:
        raise HTTPException(status_code=502, detail=str(error))
    except Exception:
        raise HTTPException(status_code=502, detail="Knowledge-base audit failed")
