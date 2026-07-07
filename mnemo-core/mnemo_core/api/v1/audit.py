from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

router = APIRouter(prefix="/audit")


class AuditEntry(BaseModel):
    id: int
    actor: str
    action: str
    status: int
    details: dict[str, Any]
    created_at: str


@router.get("", response_model=list[AuditEntry])
async def list_audit(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEntry]:
    return [
        AuditEntry.model_validate(entry)
        for entry in request.app.state.job_store.list_audit(limit=limit)
    ]
