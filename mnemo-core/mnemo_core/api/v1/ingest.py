import logging

from fastapi import APIRouter, Depends, HTTPException

from ...models import DocumentInput, IngestResult
from ...pipeline import PipelineError
from ...pipeline.runner import PipelineRunner
from ..deps import get_runner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=IngestResult)
async def ingest(
    req: DocumentInput,
    runner: PipelineRunner = Depends(get_runner),
) -> IngestResult:
    """Full pipeline in one call: classify, augment, format, commit, and raise a PR."""
    try:
        return await runner.run(req)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error during ingest")
        raise HTTPException(status_code=500, detail="Internal server error") from None
